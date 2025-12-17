from kazoo.client import KazooClient
from kazoo.recipe.barrier import Barrier
from kazoo.recipe.counter import Counter
from kazoo.recipe.election import Election
import threading
import time
import random
import signal
import numpy as np
from kazoo.recipe.watchers import ChildrenWatch, DataWatch
import requests

def watch_api_url(data, stat):
    if(data):
        global API_URL
        API_URL = data.decode("utf-8")
        print("API_URL:", API_URL)
    else:
        exit(0)
    return True

def watch_sampling_period(data, stat):
    if(data):
        global SAMPLING_PERIOD
        SAMPLING_PERIOD = float(data.decode("utf-8"))
        print("SAMPLING_PERIOD:", SAMPLING_PERIOD)
    else:
        exit(0)
    return True

def watch_devices(children):
    print("Change in devices:", children)

# Definir una función que se ejecuta cuando se recibe la señal de interrupción
def interrupt_handler(signal, frame):
    global barrier
    barrier.create()
    exit(0)

def request(valor):
    url = f'http://{API_URL}/nuevo'
    params = {'dato': {valor}}
    response = requests.get(url, params=params)
    print(response.status_code)

# Registrar la función como el manejador de la señal de interrupción
signal.signal(signal.SIGINT, interrupt_handler)

# Crear un identificador para la aplicación
id = input("Introduce un identificador: ")

# Crear un cliente kazoo y conectarlo con el servidor zookeeper
client = KazooClient(hosts="127.0.0.1:2181")
client.start()

# Crear una elección entre las aplicaciones y elegir un líder
election = Election(client, "/election", id)
barrier = Barrier(client, "/barrier")
counter = Counter(client, "/counter")

client.ensure_path("/mediciones")


# Definir una función que se ejecuta cuando una aplicación es elegida líder
def leader_func():
    global counter
    counter -= counter.value
    ChildrenWatch(client, "/mediciones", watch_devices)

    while True:
        barrier.create()
        print("Soy lider")
        time.sleep(SAMPLING_PERIOD)
        # Obtener los hijos de /mediciones
        list = []
        children = client.get_children("/mediciones")
        for child in children:
            list.append(int(client.get(f"/mediciones/{child}")[0].decode('utf-8')))
        barrier.remove()
        # Calcular la media de los valores
        mean = np.mean(list)
        # Mostrar la media por consola
        print(f"Media: {mean}")
        # Enviar la media usando requests
        request(mean)



# Definir una función que se encarga de lanzar la parte de la elección
def election_func():
    # Participar en la elección con el identificador de la aplicación
    election.run(leader_func)


# Crear un hilo para ejecutar la función election_func
election_thread = threading.Thread(target=election_func, daemon=True)
# Iniciar el hilo
election_thread.start()

client.create(f"/mediciones/{id}", ephemeral=True)

DataWatch(client, "/config/sampling_period", watch_sampling_period)
DataWatch(client, "/config/api_url", watch_api_url)

# Enviar periódicamente un valor a una subruta de /mediciones con el identificador de la aplicación
while True:
    # Generar una nueva medición aleatoria
    value = random.randint(75, 85)

    # Actualizar el valor de /values asociado al nodo
    client.set(f"/mediciones/{id}", value.__str__().encode())

    counter += 1

    print("Número de mediciones:", counter.value)
    # Esperar al lider
    barrier.wait()
