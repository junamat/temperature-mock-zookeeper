import os
import sys
import threading
import time
import random
import signal
import numpy as np
import requests

from kazoo.client import KazooClient
from kazoo.recipe.barrier import Barrier
from kazoo.recipe.counter import Counter
from kazoo.recipe.election import Election
from kazoo.recipe.watchers import ChildrenWatch, DataWatch
from kazoo.exceptions import KazooException, ConnectionLoss, SessionExpiredException
from kazoo.retry import KazooRetry

MEDICIONES = "/mediciones"
API_URL = os.getenv("API_URL", "localhost:8080")
SAMPLING_PERIOD = 2


def watch_api_url(data, stat):
    if data:
        global API_URL
        API_URL = data.decode("utf-8")
        print("API_URL:", API_URL)
    return True


def watch_sampling_period(data, stat):
    if data:
        global SAMPLING_PERIOD
        SAMPLING_PERIOD = float(data.decode("utf-8"))
        print("SAMPLING_PERIOD:", SAMPLING_PERIOD)
    return True


def watch_devices(children):
    print("Change in devices:", children)


# Handler de interrupción
def interrupt_handler(signal, frame):
    global barrier
    try:
        barrier.create()
    except:
        pass
    sys.exit(0)


def request(valor):
    try:
        url = f'http://{API_URL}/nuevo'
        params = {'dato': {valor}}
        response = requests.get(url, params=params, timeout=1)  # Timeout para no bloquear
        print(response.status_code)
    except Exception as e:
        print("Error en request:", e)


signal.signal(signal.SIGINT, interrupt_handler)

if len(sys.argv) != 2:
    id = input("Introduce un identificador: ")
else:
    id = sys.argv[1]

ZOOKEEPER_HOSTS = os.getenv("ZOOKEEPER_HOSTS", "localhost:2181")

retry_policy = KazooRetry(max_tries=-1, delay=0.5, max_delay=2)

print(f"Conectando a: {ZOOKEEPER_HOSTS}")
client = KazooClient(hosts=ZOOKEEPER_HOSTS, connection_retry=retry_policy)
client.start()

election = Election(client, "/election", id)
barrier = Barrier(client, "/barrier")
counter = Counter(client, "/counter")

client.ensure_path(MEDICIONES)
try:
    barrier.create()
except KazooException:
    pass


def leader_func():
    global counter
    try:
        counter -= counter.value
        ChildrenWatch(client, MEDICIONES, watch_devices)
    except Exception:
        pass

    while True:
        try:
            print("Soy lider")
            time.sleep(SAMPLING_PERIOD)

            # Obtener hijos
            _list = []
            children = client.get_children(MEDICIONES)
            for child in children:
                try:
                    data, _ = client.get(f"{MEDICIONES}/{child}")
                    _list.append(int(data.decode('utf-8')))
                except (ValueError, KazooException):
                    continue  # Si un nodo falla al leer, lo saltamos

            if _list:
                mean = np.mean(_list)
                print(f"Media: {mean}")
                request(mean)

            print("Ciclo de barrera...")
            try:
                barrier.remove()
            except KazooException:
                pass

            try:
                barrier.create()
            except KazooException:
                pass

        except (ConnectionLoss, SessionExpiredException):
            print("Lider: Perdida de conexión temporal... reintentando")
            time.sleep(1)
        except Exception as e:
            print(f"Error inesperado en lider: {e}")
            time.sleep(1)


def election_func():
    while True:
        try:
            election.run(leader_func)
        except (ConnectionLoss, SessionExpiredException):
            print("Elección: Conexión perdida, reintentando elección...")
            time.sleep(1)
        except Exception as e:
            print(f"Error en elección: {e}")
            time.sleep(2)


election_thread = threading.Thread(target=election_func, daemon=True)
election_thread.start()

# Configuración de Watchers
if client.exists("/config/sampling_period"):
    DataWatch(client, "/config/sampling_period", watch_sampling_period)
if client.exists("/config/api_url"):
    DataWatch(client, "/config/api_url", watch_api_url)

while True:
    try:
        # Generar medición
        value = random.randint(75, 85)

        node_path = f"{MEDICIONES}/{id}"
        if client.exists(node_path) is None:
            print("Re-creando nodo efímero tras desconexión...")
            client.create(node_path, ephemeral=True)

        client.set(node_path, str(value).encode())

        try:
            counter += 1
            print("Número de mediciones:", counter.value)
        except KazooException:
            print("No se pudo actualizar contador (sin red)")

        print("Esperando barrera...")
        barrier.wait(timeout=SAMPLING_PERIOD * 2)  # Timeout para no quedarse pillado eternamente si el líder muere

        # Buffer
        time.sleep(SAMPLING_PERIOD / 100)

    except (ConnectionLoss, SessionExpiredException):
        print("⚠️ Conexión perdida con Zookeeper. Reintentando...")
        # Dormimos un poco para dar tiempo a Kazoo a reconectar en background
        time.sleep(1)
    except Exception as e:
        print(f"Error en bucle principal: {e}")
        time.sleep(1)