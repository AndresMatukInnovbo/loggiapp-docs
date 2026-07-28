# Servicio: updateShipment

!!! danger "NO IMPLEMENTADO"

    Este servicio está definido en el contrato oficial de Monitor (DD-EST-02) pero **LoggiApp no lo implementa actualmente**. No existe código, DTOs, ni lógica de negocio.

## Propósito según contrato oficial

Actualizar un despacho ya creado en Monitor. Permite modificar datos del manifiesto, ruta, vehículo, conductor y órdenes de carga después de la creación inicial.

## Impacto de no tenerlo

Si los datos de un despacho cambian después del inicio del viaje (ej: cambio de conductor, cambio de ruta, corrección de datos), Monitor no se entera. La información queda desactualizada.

## Cobertura actual

| Categoría              | Contrato Monitor   | LoggiApp implementa | Cobertura |
| ---------------------- | ------------------ | ------------------- | ---------:|
| Actualizar despacho    | `updateShipment`   | No                  |        0% |
