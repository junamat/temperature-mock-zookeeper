# Sistema de Sensores Distribuidos con Zookeeper

Implementa un clúster de sensores coordinados mediante **Apache Zookeeper** y **Docker**.

## Descripción

El sistema despliega múltiples sensores (contenedores Python) que:
1.  Se coordinan para tomar mediciones simultáneas (Mediante el uso de una **Barrier**).
2.  Eligen un **Líder** democráticamente.
3.  El Líder agrega los datos y los envía a una [API REST central](https://github.com/junamat/docker-replication-example/tree/main).
4.  Permiten configuración dinámica en tiempo real.

## Estructura del Proyecto

* `main.py`: Lógica del sensor (Kazoo, Election, Barrier, Watchers).
* `init_config.py`: Script para inyectar configuración dinámica en Zookeeper (sin uso al dockerizar).
* `docker-compose.yml`: Cluster sin ZK Ensemble.
* `docker-compose-cluster.yml`: Definición del stack completo (ZK Ensemble + Apps + Backend).
* `Dockerfile`: Definición de la imagen del sensor (`apfnam/zk_temp`).

## Requisitos

* Docker y Docker Compose.
* Puertos libres: 2181-2183 (ZK), 4000 (Web), 3000 (Grafana).

## Puesta en Marcha

### 1. Construir la imagen
Paso que no debería ser necesario excepto si haces cualquier modificación:

```bash
$ docker build -t apfnam/zk_temp .

```

### 2. Desplegar el Clúster

Este comando levanta los 3 nodos de Zookeeper, los 3 sensores y el backend (Redis/Web/Serving):

```bash
$ docker compose -f docker-compose-cluster.yml up

```

También puedes iniciar la versión con una sola instancia de zk haciendo
```bash
$ docker compose -f docker-compose.yml up # aunque por defecto se supone que busca un archivo con este nombre y por tanto no habría que especificarlo.
```
pEsperar unos segundos hasta que los nodos de Zookeeper estén "healthy".

### 3. Verificar funcionamiento

* **Ver Logs:** Comprueba la coordinación en los logs. Verás al líder calculando medias y a los seguidores esperando en la barrera.
```bash

$ docker logs -f practica3-1

```


* **Ver Líder Zookeeper:** Comprueba el estado del ensemble ZK.
```bash
$ docker exec zookeeper1 zkServer.sh status
$ docker exec zookeeper2 zkServer.sh status
$ docker exec zookeeper3 zkServer.sh status

```


* **Grafana:** Entra en `http://localhost:3000` para ver las mediciones llegando en tiempo real.
