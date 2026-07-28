# Servicio: upsertCargo

!!! danger "NO IMPLEMENTADO"

    Este servicio está definido en el contrato oficial de Monitor (DD-EST-02) pero **LoggiApp no lo implementa actualmente**. No existe código, DTOs, ni lógica de negocio.

## Propósito según contrato oficial

Insertar o actualizar una orden de carga (remesa) individual, sin necesidad de enviar todo el despacho. Permite agregar remesas nuevas a un despacho existente o modificar las existentes.

## Impacto de no tenerlo

No se pueden agregar remesas a un despacho ya creado en Monitor. Todas las remesas deben existir al momento del `loadShipment`.

## Cobertura actual

| Categoría                  | Contrato Monitor | LoggiApp implementa | Cobertura |
| -------------------------- | ---------------- | ------------------- | ---------:|
| Insertar/actualizar remesa | `upsertCargo`    | No                  |        0% |
