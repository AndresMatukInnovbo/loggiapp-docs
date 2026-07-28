# Servicio: finalizeShipment

## 1. Nombre

`finalizeShipment`

## 2. Objetivo

Este servicio **finaliza un despacho en la plataforma Monitor**, indicando que el viaje ha concluido y el manifiesto puede darse por terminado. Una vez finalizado, Monitor deja de monitorear activamente el despacho.

## 3. Cuándo se ejecuta

| Aspecto           | Detalle |
| ----------------- | ------- |
| **Evento**        | La carga cambia al estado `END_SERVICE` (fin del servicio / entrega completada) |
| **Actor**         | Conductor (desde la app móvil) o usuario web que actualiza el tracking |
| **Condición 1**   | El `holderId` debe ser `Companies.TECLOGI` |
| **Condición 2**   | El `idCompany` de la carga debe estar en `MonitorCargoCompanies` (Maersk Logistics) |
| **Condición 3**   | La carga NO debe haber sido finalizada previamente en Monitor (`monitorState.finalizeShipmentResponse.transmited == false`) |
| **Condición 4**   | La carga debe tener un número de manifiesto (`cargo.manifest` no vacío) |
| **Condición 5**   | La carga debe tener una fecha de fin de viaje (`cargo.durationTime.endDate` no null) |

> **Endpoint REST manual:** `POST /monitor/{cargoId}/finalize`

## 4. Flujo

```
Conductor finaliza el servicio (END_SERVICE)
        ↓
CargoBusinessImpl.tracking(action, imagesCargoRequest)
        ↓
CargoBusinessImpl.reportToMonitorCargo("END_SERVICE", cargo, holderId, ...)
        ↓
MonitorCargoBusinessImpl.finalizeMonitorShipment(cargoId, idCompany, holderId)
        ↓  [Ejecutado en thread asíncrono: monitorCargoExecutor]
¿La carga ya fue finalizada en Monitor?
        ↓ NO
validateFinalizeShipment(cargo)
        ↓
¿Errores de validación?
        ↓ NO
buildFinalizeShipmentRequest(cargo, finalizeValidator)
        ↓
MonitorServiceImpl.finalizeShipment(request, holderId)
        ↓
Monitor procesa y responde (código 000 = éxito)
        ↓
Se almacena resultado en cargo.monitorState.finalizeShipmentResponse
```

## 5. Lugares donde se llama

| Clase                     | Método                                                      | Motivo                                                                      | Condición                                             |
| ------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------- |
| `CargoBusinessImpl`       | `reportToMonitorCargo(action, cargo, holderId, ...)`        | Finalizar automáticamente el despacho cuando el conductor completa la entrega| `action == StateCargo.END_SERVICE`                    |
| `CargoServiceImpl` (REST) | `finalizeMonitorShipment(cargoId)`                          | Endpoint REST para finalizar manualmente                                    | `POST /monitor/{cargoId}/finalize`                    |

## 6. Datos enviados a Monitor

| Campo LoggiApp                | Campo Monitor    | Descripción                                    | Obligatorio | Fuente                                                              |
| ----------------------------- | ---------------- | ---------------------------------------------- | :---------: | ------------------------------------------------------------------- |
| `cargo.manifest`              | `idManifest`     | Número del manifiesto a finalizar              | Sí          | `Cargo.manifest`                                                    |
| `cargo.durationTime.endDate`  | `finalizeDate`   | Fecha y hora de finalización del viaje         | Sí          | `Cargo.durationTime.endDate` → hora colombiana `yyyy-MM-dd HH:mm:ss`|

## 7. Campos de Monitor NO utilizados por LoggiApp

El contrato oficial de Monitor define exactamente los mismos campos que LoggiApp envía (`idManifest` y `finalizeDate`). **No hay campos sin utilizar para este servicio.**

## 8. Transformaciones

| Transformación                | Descripción                                                                                                                   |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Fecha a hora colombiana**   | `cargo.durationTime.endDate` (tipo `Date`) se convierte a String en zona horaria de Colombia con formato `yyyy-MM-dd HH:mm:ss` usando `DateUtil.getColombianStringDate()`. |

## 9. Request construido

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.soap.soapexposer.mayasoft.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:finalizeShipment>
      <authToken>
        <authUser>USUARIO_MONITOR</authUser>
        <authPassword>PASSWORD_MONITOR</authPassword>
      </authToken>
      <finalize>
        <idManifest>MAN-2025-001234</idManifest>
        <finalizeDate>2025-07-30 16:45:00</finalizeDate>
      </finalize>
    </ser:finalizeShipment>
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

| Código                | Acción de LoggiApp                                                                                              |
| --------------------- | --------------------------------------------------------------------------------------------------------------- |
| `000` (éxito)         | Marca `monitorState.finalizeShipmentResponse.transmited = true`. El despacho se considera finalizado en Monitor. |
| `001` (error interno) | Se reintenta **una vez** más. Si falla de nuevo, se guarda como no transmitido.                                 |
| Otros códigos         | Se almacena como fallido (`transmited = false`).                                                                |

**Persistencia del resultado:**

El resultado se almacena en `cargo.monitorState.finalizeShipmentResponse`:

- `code`: Código de respuesta
- `description`: Descripción de la respuesta
- `transmited`: `true` si fue exitoso (código 000), `false` en caso contrario

## 11. Observaciones

| #  | Observación |
| -- | ----------- |
| 1  | **Request muy simple.** Solo envía dos campos: el manifiesto y la fecha de finalización. Es el servicio más sencillo de la integración. |
| 2  | **Idempotencia.** Si `monitorState.finalizeShipmentResponse.transmited == true`, la operación se aborta sin reenviar. |
| 3  | **Reintento automático.** Si Monitor responde con error interno (código `001`), se reintenta una vez más. |
| 4  | **Requiere fecha de fin de viaje.** La validación verifica que `cargo.durationTime.endDate` no sea null. Si no existe, se almacena error de validación sin intentar la conexión. |
| 5  | **Ejecución asíncrona.** Se ejecuta en el thread pool `monitorCargoExecutor`. No bloquea la respuesta al usuario. |
| 6  | **Complemento del flujo completo.** Este servicio cierra el ciclo de vida del despacho en Monitor: `loadShipment` (crea) → `event` (monitorea) → `finalizeShipment` (cierra). |
