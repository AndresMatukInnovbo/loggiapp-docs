# Servicio: cancelShipment

## 1. Nombre

`cancelShipment`

## 2. Objetivo

Este servicio **cancela un despacho en la plataforma Monitor**, indicando que el manifiesto ya no es válido y debe ser anulado. Una vez cancelado, Monitor deja de monitorear el despacho y lo marca como cancelado en su sistema.

## 3. Cuándo se ejecuta

| Aspecto           | Detalle |
| ----------------- | ------- |
| **Evento**        | Una carga es **eliminada** (marcada como `DELETED`) en LoggiApp |
| **Actor**         | Usuario (controlador, despachador, administrador) que elimina la carga desde la interfaz web |
| **Condición 1**   | El `holderId` debe ser `Companies.TECLOGI` |
| **Condición 2**   | El `idCompany` de la carga debe estar en `MonitorCargoCompanies` (Maersk Logistics) |
| **Condición 3**   | La carga NO debe haber sido cancelada previamente en Monitor (`monitorState.cancelShipmentResponse.transmited == false`) |
| **Condición 4**   | La carga debe tener un número de manifiesto (`cargo.manifest` no vacío) |

> **Endpoint REST manual:** `POST /monitor/{cargoId}/cancel`

## 4. Flujo

```
Usuario elimina una carga en LoggiApp
        ↓
CargoBusinessImpl.markCargoAsDeleted(cargo, deletedFingerPrint, holderId)
        ↓
Se actualiza el estado a DELETED en la base de datos
        ↓
MonitorCargoBusinessImpl.cancelMonitorShipment(cargoId, idCompany, holderId)
        ↓  [Ejecutado en thread asíncrono: monitorCargoExecutor]
¿La carga ya fue cancelada en Monitor?
        ↓ NO
¿El manifiesto está vacío?
        ↓ NO
buildCancelShipmentRequest(cargo)
        ↓
MonitorServiceImpl.cancelShipment(request, holderId)
        ↓
Monitor procesa y responde (código 000 = éxito)
        ↓
Se almacena resultado en cargo.monitorState.cancelShipmentResponse
```

## 5. Lugares donde se llama

| Clase                     | Método                                              | Motivo                                                                    | Condición                                    |
| ------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------- |
| `CargoBusinessImpl`       | `markCargoAsDeleted(cargo, deletedFingerPrint, holderId)` | Cancelar automáticamente el despacho cuando una carga es eliminada  | La carga se marca como `DELETED`             |
| `CargoServiceImpl` (REST) | `cancelMonitorShipment(cargoId)`                    | Endpoint REST para cancelar manualmente                                   | `POST /monitor/{cargoId}/cancel`             |

## 6. Datos enviados a Monitor

| Campo LoggiApp    | Campo Monitor   | Descripción                          | Obligatorio | Fuente           |
| ----------------- | --------------- | ------------------------------------ | :---------: | ---------------- |
| `cargo.manifest`  | `idManifest`    | Número del manifiesto a cancelar     | Sí          | `Cargo.manifest` |

## 7. Campos de Monitor NO utilizados por LoggiApp

El contrato oficial de `cancelShipment` solo requiere `idManifest`. **No hay campos sin utilizar.**

!!! note "Nota"

    El contrato también documenta un servicio `cancelCargo` (para cancelar/eliminar una orden de carga individual) con campos `idManifest`, `idCargo` y `delete`. LoggiApp **no implementa `cancelCargo`** — solo cancela el despacho completo.

## 8. Transformaciones

No aplica. El único dato enviado es `cargo.manifest` directamente, sin ninguna transformación.

## 9. Request construido

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.soap.soapexposer.mayasoft.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:cancelShipment>
      <authToken>
        <authUser>USUARIO_MONITOR</authUser>
        <authPassword>PASSWORD_MONITOR</authPassword>
      </authToken>
      <cancel>
        <idManifest>MAN-2025-001234</idManifest>
      </cancel>
    </ser:cancelShipment>
  </soapenv:Body>
</soapenv:Envelope>
```

## 10. Respuesta esperada

```xml
<return>
  <code>000</code>
  <description>TRANSACCION EXITOSA</description>
</return>
```

**Interpretación por LoggiApp:**

| Código                | Acción de LoggiApp                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------- |
| `000` (éxito)         | Marca `monitorState.cancelShipmentResponse.transmited = true`. El despacho se considera cancelado en Monitor.  |
| `001` (error interno) | Se reintenta **una vez** más. Si falla de nuevo, se guarda como no transmitido.                                |
| Otros códigos         | Se almacena como fallido (`transmited = false`).                                                               |

**Persistencia del resultado:**

El resultado se almacena en `cargo.monitorState.cancelShipmentResponse`:

- `code`: Código de respuesta
- `description`: Descripción de la respuesta
- `transmited`: `true` si fue exitoso (código 000), `false` en caso contrario

## 11. Observaciones

| #  | Observación |
| -- | ----------- |
| 1  | **Se ejecuta al eliminar la carga, NO al anularla.** La cancelación en Monitor se dispara cuando la carga se marca como `DELETED`, no cuando cambia a un estado de anulación intermedio. |
| 2  | **Request mínimo.** Solo envía el número de manifiesto. Es el servicio con menos datos de toda la integración. |
| 3  | **Idempotencia.** Si `monitorState.cancelShipmentResponse.transmited == true`, la operación se aborta sin reenviar. |
| 4  | **No cancela órdenes individuales.** LoggiApp NO implementa el servicio `cancelCargo` del contrato oficial. Solo cancela el despacho completo (`cancelShipment`). |
| 5  | **No requiere fecha de cancelación.** A diferencia de `finalizeShipment`, la cancelación no incluye fecha. Monitor registra la fecha de cancelación internamente. |
| 6  | **Ejecución asíncrona.** Se ejecuta en el thread pool `monitorCargoExecutor`. La eliminación de la carga no espera la respuesta de Monitor. |
| 7  | **Reintento automático.** Si Monitor responde con error interno (código `001`), se reintenta una vez más. |
