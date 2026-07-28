# Servicio: updateSubmittedManifest

!!! danger "NO IMPLEMENTADO"

    Este servicio está definido en el contrato oficial de Monitor (DD-EST-02) pero **LoggiApp no lo implementa actualmente**. No existe código, DTOs, ni lógica de negocio.

## Propósito según contrato oficial

Actualizar el número de radicado del manifiesto ante el RNDC (Registro Nacional de Despachos de Carga). Permite informar a Monitor el número asignado por el ministerio después de la radicación.

## Impacto de no tenerlo

Monitor no recibe el número de radicado RNDC. Si el cliente requiere que Monitor muestre el radicado del manifiesto, esta información no se sincroniza.

## Cobertura actual

| Categoría                | Contrato Monitor            | LoggiApp implementa | Cobertura |
| ------------------------ | --------------------------- | ------------------- | ---------:|
| Actualizar radicado RNDC | `updateSubmittedmanifest`   | No                  |        0% |
