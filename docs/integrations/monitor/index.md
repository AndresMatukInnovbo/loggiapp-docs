# Integración LoggiApp — Monitor

> **Versión:** 1.0  
> **Última actualización:** Julio 2026  
> **Fuente de verdad:** Código fuente de LoggiApp  
> **Contrato de referencia:** DD-EST-02 — WS Proveedor Integración TMS hacia Monitor Tiempos RNDC

---

## Introducción

Este documento describe la integración técnica y funcional entre **LoggiApp** (plataforma TMS) y **Monitor** (plataforma de monitoreo satelital).

La integración se realiza mediante servicios web SOAP expuestos por Monitor. LoggiApp actúa como **consumidor** de estos servicios, enviando información sobre despachos, eventos de rastreo, y cambios de estado de las cargas en tiempo real.

### Alcance

Este documento refleja **exclusivamente** lo que el código fuente de LoggiApp implementa actualmente. No es una copia del manual oficial de Monitor. Si existe una diferencia entre el contrato oficial y el código, se documenta lo que realmente hace el código.

### Audiencia

- Clientes que desean evaluar si la integración actual cubre sus necesidades.
- Integradores y arquitectos que requieran entender los flujos técnicos.
- Desarrolladores que mantengan o extiendan la integración.

---

## Servicios documentados (implementados en LoggiApp)

| #   | Servicio                                            | Estado en LoggiApp                          |
| --- | --------------------------------------------------- | ------------------------------------------- |
| 1   | [loadShipment](load-shipment.md)                    | Activo                                      |
| 2   | [event](event.md)                                   | Activo                                      |
| 3   | [image](image.md)                                   | Implementado pero NO activo (sin callers)   |
| 4   | [finalizeShipment](finalize-shipment.md)            | Activo                                      |
| 5   | [cancelShipment](cancel-shipment.md)                | Activo                                      |

---

## Servicios del contrato oficial NO implementados en LoggiApp

Los siguientes servicios están definidos en el contrato oficial de Monitor (DD-EST-02) pero **LoggiApp no los implementa actualmente**. No existe código, DTOs, ni lógica de negocio para ninguno de ellos.

| #   | Servicio Monitor            | Propósito según contrato oficial | Impacto de no tenerlo |
| --- | --------------------------- | -------------------------------- | --------------------- |
| 1   | [`updateShipment`](update-shipment.md)            | Actualizar un despacho ya creado en Monitor. Permite modificar datos del manifiesto, ruta, vehículo, conductor y órdenes de carga después de la creación inicial. | Si los datos de un despacho cambian después del inicio del viaje (ej: cambio de conductor, cambio de ruta, corrección de datos), Monitor no se entera. La información queda desactualizada. |
| 2   | [`upsertCargo`](upsert-cargo.md)               | Insertar o actualizar una orden de carga (remesa) individual, sin necesidad de enviar todo el despacho. Permite agregar remesas nuevas a un despacho existente o modificar las existentes. | No se pueden agregar remesas a un despacho ya creado en Monitor. Todas las remesas deben existir al momento del `loadShipment`. |
| 3   | [`cancelCargo`](cancel-cargo.md)               | Cancelar o eliminar una orden de carga (remesa) individual dentro de un despacho. Permite marcar una remesa como cancelada sin afectar el despacho completo. | Si una remesa se cancela en LoggiApp, Monitor sigue mostrándola como activa. Solo se puede cancelar el despacho completo (`cancelShipment`), no remesas individuales. |
| 4   | [`logisticTime`](logistic-time.md)              | Subir tiempos logísticos detallados a una orden de carga: llegada al sitio de cargue, inicio de cargue, fin de cargue, salida del sitio de cargue, llegada al sitio de descargue, inicio de descargue, fin de descargue. | Monitor no recibe los tiempos logísticos reales de cargue/descargue. Solo recibe el evento de "llegada" (vía `event`), pero no los tiempos de inicio/fin de las operaciones de carga y descarga. |
| 5   | [`updateSubmittedmanifest`](update-submitted-manifest.md)   | Actualizar el número de radicado del manifiesto ante el RNDC (Registro Nacional de Despachos de Carga). Permite informar a Monitor el número asignado por el ministerio después de la radicación. | Monitor no recibe el número de radicado RNDC. Si el cliente requiere que Monitor muestre el radicado del manifiesto, esta información no se sincroniza. |

---

## Resumen de cobertura

| Categoría                      | Contrato Monitor            | LoggiApp implementa                       | Cobertura |
| ------------------------------ | --------------------------- | ----------------------------------------- | ---------:|
| Crear despacho                 | `loadShipment`              | Sí                                        |      100% |
| Actualizar despacho            | `updateShipment`            | No                                        |        0% |
| Insertar/actualizar remesa     | `upsertCargo`               | No                                        |        0% |
| Cancelar remesa                | `cancelCargo`               | No                                        |        0% |
| Cancelar despacho              | `cancelShipment`            | Sí                                        |      100% |
| Finalizar despacho             | `finalizeShipment`          | Sí                                        |      100% |
| Tiempos logísticos             | `logisticTime`              | No                                        |        0% |
| Cargar imágenes                | `image`                     | Parcial (infraestructura lista, sin uso)  |      ~10% |
| Actualizar radicado RNDC       | `updateSubmittedmanifest`   | No                                        |        0% |
| Eventos de rastreo             | `event` (no en contrato oficial) | Sí                                   |      100% |
