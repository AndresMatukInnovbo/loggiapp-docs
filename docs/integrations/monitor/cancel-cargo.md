# Servicio: cancelCargo

!!! danger "NO IMPLEMENTADO"

    Este servicio está definido en el contrato oficial de Monitor (DD-EST-02) pero **LoggiApp no lo implementa actualmente**. No existe código, DTOs, ni lógica de negocio.

## Propósito según contrato oficial

Cancelar o eliminar una orden de carga (remesa) individual dentro de un despacho. Permite marcar una remesa como cancelada sin afectar el despacho completo.

## Impacto de no tenerlo

Si una remesa se cancela en LoggiApp, Monitor sigue mostrándola como activa. Solo se puede cancelar el despacho completo (`cancelShipment`), no remesas individuales.

## Cobertura actual

| Categoría        | Contrato Monitor | LoggiApp implementa | Cobertura |
| ---------------- | ---------------- | ------------------- | ---------:|
| Cancelar remesa  | `cancelCargo`    | No                  |        0% |
