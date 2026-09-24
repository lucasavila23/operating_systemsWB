[English](README.md) | Español

# Theme park concurrency sim

Una simulación multihilo de un día en un parque temático, con un dashboard en directo en el navegador. Cada visitante, cada miembro del personal y el reloj funcionan en su propio hilo.

## Contexto

Proyecto de curso en grupo, IE University, Operating Systems and Parallel Computing (primavera de 2026).

## Funcionalidades

- Los visitantes deciden qué hacer según su hambre, energía, necesidad de ir al baño y uno de tres perfiles: buscador de emociones, familia o ruta eficiente.
- Las atracciones y las mesas de los restaurantes tienen capacidad limitada, controlada con semáforos. Los contadores y colas compartidos se protegen con locks.
- Eventos aleatorios: averías, cambios de tiempo, avisos VIP, ofertas relámpago y espectáculos. Durante una avería, los visitantes esperan en una variable de condición hasta que se repara la atracción.
- Un carril FastPass con embarque prioritario en cualquier atracción.
- Un dashboard en directo con el reloj del parque, la longitud de las colas, el estado de las atracciones y un registro de eventos.
- Un informe al cierre con los totales de atracciones, restaurantes y baños, y los cinco visitantes que más atracciones hicieron.

## Cómo funciona

| Concepto | Dónde |
|---|---|
| `threading.Semaphore` | Plazas en atracciones, mesas, cabinas de baño |
| `threading.Lock` / `RLock` | Colas, contadores, el contador de minutos del reloj |
| `threading.Condition` | Los visitantes se bloquean durante una avería; `notify_all()` los despierta al repararla |
| `threading.Event` | Señal de cierre del parque |
| Hilos daemon | Reloj, gestor de eventos, personal, servidor del dashboard |

Tres patrones de diseño: Strategy para los perfiles de visitante (`strategies.py`), Observer para los eventos (`events.py`) y Decorator para el FastPass (`fastpass.py`). Un servidor Flask-SocketIO envía el estado del parque a `wbpark/ui/index.html`.

## Cómo ejecutarlo

```bash
git clone https://github.com/lucasavila23/theme-park-concurrency-sim.git
cd theme-park-concurrency-sim
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --visitors 20 --speed 60 --seed 42
```

Abre `http://localhost:5050` para ver el dashboard. `--visitors` fija el número de hilos de visitantes (40 por defecto), `--speed` los minutos simulados por segundo real (60 por defecto) y `--seed` hace que una ejecución sea reproducible.

## Tecnologías

Python (threading), Flask, Flask-SocketIO.

## Estructura del proyecto

```
main.py           punto de entrada y opciones de línea de comandos
wbpark/           paquete de la simulación: reloj, parque, visitantes, atracciones, eventos, perfiles
wbpark/ui/        dashboard en un solo archivo
CHANGES.md        notas sobre la refactorización con patrones de diseño
```

## Autor

Lucas Avila Manotas · [LinkedIn](https://www.linkedin.com/in/lucas-avila23)
