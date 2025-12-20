# Coordinación en Sistemas Distribuidos con Zookeeper

Asignatura: Desarrollo de Software Crítico  
Universidad de Málaga  

---

## **1. Introducción y Objetivos**

El objetivo de esta práctica es implementar un sistema distribuido robusto utilizando **Apache Zookeeper** como middleware de coordinación. La práctica simula un entorno industrial donde múltiples nodos sensores deben tomar mediciones de forma sincronizada y reportarlas a un sistema central.

Para ello, se ha utilizado la librería **Kazoo** en Python, implementando una API simple para utilizar Zookeeper en Python.

## **2. Arquitectura del Sistema**

El sistema se ha diseñado sobre una arquitectura de contenedores orquestada con Docker Compose, dividida en tres capas:

1.  **Ensemble de Zookeeper:** Un clúster de 3 nodos (`zookeeper1`, `zookeeper2`, `zookeeper3`) configurados para trabajar en cluster, garantizando alta disponibilidad y tolerancia a fallos.
2.  **Nodos de Aplicación (Sensores):** 3 instancias del contenedor desarrollado (`practica3-X`), cada una con un ID único.
3.  **Backend de Procesamiento:** Reutilización de la API REST y base de datos (Redis) de la práctica anterior para la recepción y visualización de datos.

## **3. Detalles de Implementación**

El núcleo de la lógica se encuentra en el script `main.py` y cubre los siguientes requisitos del enunciado:

### **3.1. Elección de Líder (Leader Election)**
Se ha utilizado la receta `Election` de Kazoo. Todos los nodos participan en la elección bajo la ruta `/election`.
* **Rol del Líder:** El nodo ganador es el único encargado de agregar las mediciones de todos los nodos (calculando la media) y enviarlas a la API REST.
* **Tolerancia a Fallos:** Si el líder cae, Zookeeper detecta la pérdida de sesión (nodo efímero) y desencadena una nueva elección automáticamente.

### **3.2. Sincronización mediante Barreras (Opción A)**
Siguiendo la **Opción A** del enunciado, se ha implementado una sincronización estricta mediante `Barrier`:
1.  **Registro:** Cada nodo guarda su medición en un znode efímero `/mediciones/{id}`.
2.  **Espera:** Los nodos llaman a `barrier.wait()`, quedando bloqueados hasta que el líder autoriza el paso.
3.  **Liberación:** El líder lee los hijos en `/mediciones`, calcula la media, la envía a la API y finalmente elimina la barrera (`barrier.remove()`), permitiendo que todos los nodos inicien el siguiente ciclo simultáneamente.

### **3.3. Uso de Watchers y Configuración Dinámica**
Se han implementado los dos tipos de watchers requeridos:
* **ChildrenWatch:** El líder monitoriza la ruta `/mediciones` para detectar y loguear cuándo se conectan o desconectan nuevos dispositivos sensores.
* **DataWatch:** Todos los nodos monitorizan las rutas `/config/sampling_period` y `/config/api_url`. Esto permite cambiar el comportamiento del clúster en tiempo real ejecutando el script auxiliar `init_config.py`, sin necesidad de reiniciar los contenedores.

### **3.4. Contador Distribuido**
Como se solicita en la Opción A, se utiliza un `Counter` distribuido en `/counter`. Cada sensor incrementa este contador atómico tras superar la barrera, llevando un registro global del número de mediciones tomadas por el clúster.

## **4. Despliegue con Docker Compose**

El fichero `docker-compose-cluster.yml` integra la solución completa; `docker-compose.yml` simplemente utiliza una sola instancia de Zookeeper.

### **4.1. Healthchecks y Dependencias**
Para evitar errores de conexión al inicio (dado que Zookeeper tarda en arrancar), se ha configurado un `healthcheck` en los nodos de Zookeeper (usando `nc -z` o `echo ruok`). Los servicios de aplicación tienen una dependencia explícita (`depends_on: service_healthy`) para asegurar que no inicien hasta que el clúster ZK esté operativo.

### **4.2. Red y Comunicación**
Los contenedores se comunican a través de la red interna `zk-network`. Las peticiones a la API utilizan el nombre del servicio interno (`web`) y su puerto interno (80), que se define de forma implícita al hacer una request http, no el expuesto al host, garantizando la comunicación dentro de la red Docker.

## 5. Problemas detectados

* Si se elige un timeout entre mediciones muy largo el sistema tiende a implosionar debido a que Zookeeper no detecta ningún input en demasiado tiempo (por defecto 10s) y decide cerrar el flujo TCP. Esto es configurable pero no es tan relevante para exponer el funcionamiento de Zookeeper.
* Mientras que se elige un nuevo lider los previos seguidores van ciclando mediciones en vez de pararse en seco; Esto es debido a que le ponemos un timeout a la barrera que si se pasa la barrera se abre. Esto es necesario si queremos que el sistema esté blindado ante caidas de los nodos de Zookeeper, pues si se cae el nodo donde una de las instancias de la práctica tiene la barrera no va a ser capaz de reconectarse.
