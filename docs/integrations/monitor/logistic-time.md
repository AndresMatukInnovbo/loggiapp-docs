# Servicio: logisticTime

!!! danger "NO IMPLEMENTADO"

    Este servicio está definido en el contrato oficial de Monitor (DD-EST-02) pero **LoggiApp no lo implementa actualmente**. No existe código, DTOs, ni lógica de negocio.

## Propósito según contrato oficial

Subir tiempos logísticos detallados a una orden de carga: llegada al sitio de cargue, inicio de cargue, fin de cargue, salida del sitio de cargue, llegada al sitio de descargue, inicio de descargue, fin de descargue.

## Impacto de no tenerlo

Monitor no recibe los tiempos logísticos reales de cargue/descargue. Solo recibe el evento de "llegada" (vía `event`), pero no los tiempos de inicio/fin de las operaciones de carga y descarga.

## Cobertura actual

| Categoría            | Contrato Monitor | LoggiApp implementa | Cobertura |
| -------------------- | ---------------- | ------------------- | ---------:|
| Tiempos logísticos   | `logisticTime`   | No                  |        0% |
