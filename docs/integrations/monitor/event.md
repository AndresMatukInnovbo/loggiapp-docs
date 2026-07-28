# Servicio: event

## 1. Nombre

`event`

## 2. Objetivo

Este servicio **reporta eventos de rastreo y monitoreo a la plataforma Monitor** asociados a un despacho activo. Permite informar a Monitor sobre:

- **Llegada al sitio de carga** (zona de cargue)
- **Llegada al sitio de descarga** (zona de descargue)
- **Posición GPS del vehículo** (rastreo satelital desde Satrack)
- **Reportes manuales de ubicación/anomalía** (registrados por el conductor o controlador)

Monitor utiliza estos eventos para alimentar su sistema de monitoreo en tiempo real, permitiendo al controlador visualizar la ubicación, velocidad, alertas y estado del vehículo durante el viaje.

## 3. Cuándo se ejecuta

El servicio `event` se invoca en **cuatro escenarios** diferentes:

| Escenario                          | Evento                                                          | Actor                    | Condición                                                                                                                  |
| ---------------------------------- | --------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **Loadzone (zona de carga)**       | La carga cambia a estado `START_TRIP`                           | Conductor / Sistema      | Se ejecuta inmediatamente después del `loadShipment`. Requiere que `durationTime.startDate` esté registrada.               |
| **Downloadzone (zona de descarga)**| La carga cambia a estado `DESTINATION_ARRIVED`                  | Conductor                | Se activa cuando el conductor reporta la llegada a un punto de destino específico (`addressId` + `destinationId`).         |
| **Satrack GPS (rastreo satelital)**| Se recibe un evento GPS de Satrack con cambio de estado         | Sistema (automático)     | Proceso de polling de Satrack detecta evento con coordenadas válidas y hay un cambio de estado del vehículo.               |
| **Last Tracking (reporte manual)** | Un conductor o controlador registra un punto de trazabilidad    | Conductor / Controlador  | Se ejecuta cuando se registra un `TracePoint` manualmente en el sistema.                                                   |

## 4. Flujo

### Flujo Loadzone (Zona de carga)

```
Conductor inicia viaje (START_TRIP)
        ↓
registerMonitorLoadShipmentAndLoadzoneEvent(...)
        ↓  [Ejecutado en thread asíncrono]
registerMonitorLoadShipmentSync(...) → loadShipment (ya documentado)
        ↓
registerLoadzoneEventSync(...)
        ↓
¿El evento de loadzone ya fue registrado?
        ↓ NO
validateEvent(cargo, "loadzone")
        ↓
buildEventRequest(cargo, "loadzone", eventValidator)
        ↓
MonitorServiceImpl.event(eventRequest, holderId)
        ↓
Se almacena resultado en cargo.monitorState.loadZoneEventResponse
```

### Flujo Downloadzone (Zona de descarga)

```
Conductor reporta llegada a destino (DESTINATION_ARRIVED)
        ↓
CargoBusinessImpl.tracking(action, imagesCargoRequest)
        ↓
reportToMonitorCargo("DESTINATION_ARRIVED", ...)
        ↓
MonitorCargoBusinessImpl.registerDownloadzoneEvent(cargoId, holderId, addressId, destinationId, idCompany)
        ↓  [Ejecutado en thread asíncrono]
¿El evento para ese addressId + destinationId ya fue registrado?
        ↓ NO
validateEvent(cargo, "downloadzone", addressId, destinationId)
        ↓
buildEventRequest(cargo, "downloadzone", eventValidator, addressId, destinationId)
        ↓
MonitorServiceImpl.event(eventRequest, holderId)
        ↓
Se almacena resultado en cargo.monitorState.downloadZoneEventResponse
Se crea registro en sub-colección de downloadZoneEvents
```

### Flujo Satrack GPS (Rastreo satelital)

```
Proceso batch de polling Satrack (periódico)
        ↓
CargoBusinessImpl.registerLastEventSatrack(cargos, holderId)
        ↓
Para cada cargo con evento GPS nuevo:
  ¿Hay cambio de estado del vehículo?
        ↓ SÍ
  MonitorCargoBusinessImpl.registerSatrackEvent(holderId, cargoId, idCompany, satrackEvent, generationDate)
        ↓  [Ejecutado en thread asíncrono]
  validateEvent(cargo, generationDate, satrackDate)
        ↓
  buildEventRequest(cargo, eventValidator, satrackEvent)
        ↓
  MonitorServiceImpl.event(eventRequest, holderId)
        ↓
  Se almacena resultado en cargo.monitorState.lastTrackingEventResponse
  Se crea registro en historial de lastTrackingMonitor
```

### Flujo Last Tracking (Reporte manual)

```
Conductor/Controlador registra punto de trazabilidad
        ↓
CargoBusinessImpl.registerTracePoint(cargoId, lastPointLocation)
        ↓
MonitorCargoBusinessImpl.registerLastTrackingEvent(holderId, cargoId, idCompany, tracePoint, userId, appType)
        ↓  [Ejecutado en thread asíncrono]
validateEvent(cargo, tracePoint)
        ↓
buildEventRequest(cargo, eventValidator, tracePoint)
        ↓
MonitorServiceImpl.event(eventRequest, holderId)
        ↓
Se almacena resultado en cargo.monitorState.lastTrackingEventResponse
Se crea registro en historial de lastTrackingMonitor
```

## 5. Lugares donde se llama

| Clase                        | Método                                                                | Motivo                                                        | Condición                                                                       |
| ---------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `MonitorCargoBusinessImpl`   | `registerLoadzoneEventSync(...)`                                      | Reportar llegada al sitio de cargue                           | Ejecutado secuencialmente después del loadShipment con `START_TRIP`              |
| `MonitorCargoBusinessImpl`   | `registerDownloadzoneEvent(...)`                                      | Reportar llegada al sitio de descargue                        | `action == DESTINATION_ARRIVED` y evento no registrado para esa dirección       |
| `MonitorCargoBusinessImpl`   | `registerSatrackEvent(...)`                                           | Reportar posición GPS y estado del vehículo desde Satrack     | Polling detecta coordenadas válidas y cambio de estado                          |
| `MonitorCargoBusinessImpl`   | `registerLastTrackingEvent(...)`                                      | Reportar novedad/anomalía registrada manualmente              | Conductor o controlador registra un `TracePoint`                                |
| `CargoBusinessImpl`          | `reportToMonitorCargo(...)`                                           | Orquesta la llamada según el estado del tracking              | `START_TRIP` → loadzone, `DESTINATION_ARRIVED` → downloadzone                  |
| `CargoBusinessImpl`          | `registerLastEventSatrack(...)`                                       | Proceso batch de rastreo GPS Satrack                          | Ejecutado periódicamente para cargas activas                                    |
| `CargoBusinessImpl`          | `registerTracePoint(...)`                                             | Registro manual de punto de ubicación/anomalía                | TracePoint cumple requisitos mínimos                                            |
| `CargoServiceImpl` (REST)    | `registerLoadzoneEvent(cargoId)`                                      | Endpoint: `POST /monitor/{cargoId}/loadzone-event`            | Invocación directa                                                              |
| `CargoServiceImpl` (REST)    | `registerDownloadzoneEvent(cargoId, addressId, destinationId)`        | Endpoint: `POST /monitor/{cargoId}/downloadzone-event`        | Invocación directa con parámetros                                               |
| `CargoServiceImpl` (REST)    | `registerLastTrackingEvent(cargoId, tracePoint)`                      | Endpoint: `POST /monitor/{cargoId}/last-tracking-event`       | Invocación directa con body                                                     |

## 6. Datos enviados a Monitor

### Estructura común a todos los eventos

| Campo LoggiApp        | Campo Monitor       | Descripción                            | Obligatorio | Fuente                        |
| --------------------- | ------------------- | -------------------------------------- | :---------: | ----------------------------- |
| `cargo.manifest`      | `idManifest`        | Número del manifiesto del despacho     | Sí          | `Cargo.manifest`              |
| _(varía según tipo)_  | `eventCode`         | Código del tipo de evento              | Sí          | Ver tabla de códigos abajo    |
| _(varía según tipo)_  | `eventDate`         | Fecha y hora del evento                | Sí          | Ver detalle por tipo          |
| _(varía según tipo)_  | `eventDescription`  | Descripción textual del evento         | Sí          | Ver detalle por tipo          |
| _(varía según tipo)_  | `latitude`          | Latitud de la ubicación                | No          | Ver detalle por tipo          |
| _(varía según tipo)_  | `longitude`         | Longitud de la ubicación               | No          | Ver detalle por tipo          |
| _(varía según tipo)_  | `location`          | Dirección/descripción de la ubicación  | No          | Ver detalle por tipo          |
| _(varía según tipo)_  | `state`             | Estado del vehículo                    | No          | Ver detalle por tipo          |
| _(varía según tipo)_  | `velocity`          | Velocidad del vehículo                 | No          | Ver detalle por tipo          |
| _(varía según tipo)_  | `temperature`       | Temperatura registrada                 | No          | Ver detalle por tipo          |

### Códigos de evento utilizados por LoggiApp

| Código Monitor   | Constante                       | Cuándo se usa                                                               |
| ---------------- | ------------------------------- | --------------------------------------------------------------------------- |
| `loadzone`       | `MonitorEventType.LOADZONE`     | Llegada al sitio de cargue                                                  |
| `downloadzone`   | `MonitorEventType.DOWNLOADZONE` | Llegada al sitio de descargue                                               |
| `lastgps`        | `MonitorEventType.LAST_GPS`     | Reporte GPS de Satrack (por defecto)                                        |
| `lasttracking`   | `MonitorEventType.LASTTRACKING` | Reporte manual de ubicación/anomalía                                        |
| `speeding`       | `MonitorEventType.SPEEDING`     | Exceso de velocidad (Satrack evento 24, o velocidad > 75 km/h)              |
| `badgps`         | `MonitorEventType.BAD_GPS`      | Desconexión de antena GPS (Satrack evento 27)                               |
| `deviation`      | `MonitorEventType.DEVIATION`    | Giro repentino / desviación de ruta (Satrack evento 600)                    |

### Detalle por tipo de evento

#### Evento Loadzone (zona de carga)

| Campo LoggiApp                                                                         | Campo Monitor       | Fuente                                                                       |
| -------------------------------------------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------- |
| `cargo.cargoFeature.uploadDownload.origin.addresses[0].durationTime.startDate`         | `eventDate`         | Fecha de llegada al sitio de cargue (hora colombiana, `yyyy-MM-dd HH:mm:ss`) |
| _(fijo: `"loadzone"`)_                                                                 | `eventCode`         | Constante                                                                    |
| _(fijo: `"Llegó al cargue"`)_                                                         | `eventDescription`  | Texto fijo                                                                   |
| `origin.addresses[0].location.lat`                                                     | `latitude`          | Latitud del sitio de cargue                                                  |
| `origin.addresses[0].location.lng`                                                     | `longitude`         | Longitud del sitio de cargue                                                 |
| `origin.addresses[0].address`                                                          | `location`          | Dirección del sitio de cargue (truncada a 500 caracteres)                    |
| _(fijo: `""`)_                                                                         | `state`             | Vacío                                                                        |
| _(fijo: `""`)_                                                                         | `velocity`          | Vacío                                                                        |
| _(fijo: `""`)_                                                                         | `temperature`       | Vacío                                                                        |

#### Evento Downloadzone (zona de descarga)

| Campo LoggiApp                                                                                               | Campo Monitor       | Fuente                                                                          |
| ------------------------------------------------------------------------------------------------------------ | ------------------- | ------------------------------------------------------------------------------- |
| `cargo.cargoFeature.uploadDownload.destination[destinationId].addresses[addressId].durationTime.startDate`    | `eventDate`         | Fecha de llegada al sitio de descargue (hora colombiana, `yyyy-MM-dd HH:mm:ss`) |
| _(fijo: `"downloadzone"`)_                                                                                   | `eventCode`         | Constante                                                                       |
| _(fijo: `"Llegó al descargue"`)_                                                                            | `eventDescription`  | Texto fijo                                                                      |
| `destination[destinationId].addresses[addressId].location.lat`                                               | `latitude`          | Latitud del sitio de descargue                                                  |
| `destination[destinationId].addresses[addressId].location.lng`                                               | `longitude`         | Longitud del sitio de descargue                                                 |
| `destination[destinationId].addresses[addressId].address`                                                    | `location`          | Dirección del sitio de descargue (truncada a 500 caracteres)                    |
| _(fijo: `""`)_                                                                                               | `state`             | Vacío                                                                           |
| _(fijo: `""`)_                                                                                               | `velocity`          | Vacío                                                                           |
| _(fijo: `""`)_                                                                                               | `temperature`       | Vacío                                                                           |

#### Evento Satrack GPS (rastreo satelital)

| Campo LoggiApp                                             | Campo Monitor       | Fuente                                                                                                                            |
| ---------------------------------------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `satrackEvent.generationDate` o `generationDate`           | `eventDate`         | Fecha del evento Satrack (formato ISO sin Z → `yyyy-MM-ddTHH:mm:ss`), o fecha de generación en hora colombiana como fallback      |
| _(dinámico)_                                               | `eventCode`         | `lastgps` por defecto. Cambia a `speeding` si evento=24 o velocidad>75. `badgps` si evento=27. `deviation` si evento=600.        |
| `satrackEvent.description`                                 | `eventDescription`  | Descripción del evento Satrack (truncada a 100 caracteres). Si es null: `"Reporte Satrack"`                                       |
| `satrackEvent.latitude`                                    | `latitude`          | Latitud reportada por GPS                                                                                                         |
| `satrackEvent.longitude`                                   | `longitude`         | Longitud reportada por GPS                                                                                                        |
| `satrackEvent.address`                                     | `location`          | Dirección geocodificada por Satrack (truncada a 500 caracteres)                                                                   |
| `satrackEvent.ignition` / `satrackEvent.vehicleStatus`     | `state`             | Estado mapeado: ignition `0`→`on`, `1`→`off`, vehicleStatus `"Detenido"`→`stopped`                                               |
| `satrackEvent.speed`                                       | `velocity`          | Velocidad del vehículo (vacío si < 0)                                                                                             |
| `satrackEvent.temperature`                                 | `temperature`       | Temperatura (parseada con `Utils.parseTemperature()`, vacío si null)                                                              |

#### Evento Last Tracking (reporte manual)

| Campo LoggiApp                  | Campo Monitor       | Fuente                                                                      |
| ------------------------------- | ------------------- | --------------------------------------------------------------------------- |
| `tracePoint.fingerprint.date`   | `eventDate`         | Fecha del reporte (hora colombiana, formato `yyyy-MM-dd HH:mm:ss`)          |
| _(fijo: `"lasttracking"`)_     | `eventCode`         | Constante                                                                   |
| `tracePoint.name`               | `eventDescription`  | Nombre/descripción del punto reportado (truncado a 100 caracteres)          |
| `tracePoint.location.lat`       | `latitude`          | Latitud del punto reportado                                                 |
| `tracePoint.location.lng`       | `longitude`         | Longitud del punto reportado                                                |
| `tracePoint.address`            | `location`          | Dirección del punto reportado (truncada a 500 caracteres)                   |
| _(fijo: `""`)_                  | `state`             | Vacío                                                                       |
| _(fijo: `""`)_                  | `velocity`          | Vacío                                                                       |
| _(fijo: `""`)_                  | `temperature`       | Vacío                                                                       |

## 7. Campos de Monitor NO utilizados por LoggiApp

El servicio `event` de Monitor no está documentado como un servicio independiente en el contrato oficial DD-EST-02. Es un servicio personalizado/extendido que LoggiApp consume. Sin embargo, comparando con la estructura del DTO:

- **No se envía información de la remesa/orden específica** dentro del evento (solo se asocia al manifiesto general).
- **No se utiliza un campo de "idCargo"** dentro del evento para identificar una remesa particular.

!!! note "Nota"

    El contrato oficial de Monitor no documenta un servicio `event` con esta estructura. Esto indica que es una funcionalidad adicional o un servicio extendido acordado directamente entre LoggiApp y Monitor fuera del contrato estándar DD-EST-02.

## 8. Transformaciones

| Transformación                              | Descripción                                                                                                       |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Fechas a hora colombiana**                | Todas las fechas se convierten a zona horaria de Colombia usando `DateUtil.getColombianStringDate()` con formato `yyyy-MM-dd HH:mm:ss`. |
| **Fecha Satrack ISO**                       | El formato Satrack `yyyy-MM-ddTHH:mm:ssZ` se convierte eliminando la "Z" final, resultando en `yyyy-MM-ddTHH:mm:ss`. |
| **Truncado de eventDescription**            | Se trunca a máximo 100 caracteres usando `Utils.truncate()`.                                                      |
| **Truncado de location**                    | Se trunca a máximo 500 caracteres usando `Utils.truncate()`.                                                      |
| **Mapeo de estado del vehículo**            | Ignition Satrack: `0` → `on`, `1` → `off`. VehicleStatus Satrack: `"Detenido"` → `stopped`.                      |
| **Mapeo de evento Satrack a código Monitor**| Evento 24 → `speeding`. Evento 27 → `badgps`. Evento 600 → `deviation`. Otros → `lastgps`.                       |
| **Velocidad > 75 como speeding**            | Si la velocidad reportada supera 75 km/h, el código de evento se sobreescribe a `speeding` independientemente del evento original. |
| **Temperatura**                             | Se parsea usando `Utils.parseTemperature()` y se convierte a String. Si es null, se envía vacío.                  |
| **Coordenadas**                             | Se convierten de `double`/`Double` a `String` usando `String.valueOf()`.                                          |
| **CDATA wrapping**                          | Los campos `eventDescription` y `location` se envuelven en `<![CDATA[...]]>` después de la conversión XML.        |

## 9. Request construido

### Ejemplo: Evento Loadzone (llegada al cargue)

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.soap.soapexposer.mayasoft.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:event>
      <authToken>
        <authUser>USUARIO_MONITOR</authUser>
        <authPassword>PASSWORD_MONITOR</authPassword>
      </authToken>
      <event>
        <eventCode>loadzone</eventCode>
        <eventDate>2025-07-28 09:15:00</eventDate>
        <eventDescription><![CDATA[Llegó al cargue]]></eventDescription>
        <idManifest>MAN-2025-001234</idManifest>
        <latitude>4.710989</latitude>
        <longitude>-74.072092</longitude>
        <location><![CDATA[Calle 80 #45-23 Bodega 5, Bogotá]]></location>
        <state></state>
        <velocity></velocity>
        <temperature></temperature>
      </event>
    </ser:event>
  </soapenv:Body>
</soapenv:Envelope>
```

### Ejemplo: Evento Downloadzone (llegada al descargue)

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.soap.soapexposer.mayasoft.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:event>
      <authToken>
        <authUser>USUARIO_MONITOR</authUser>
        <authPassword>PASSWORD_MONITOR</authPassword>
      </authToken>
      <event>
        <eventCode>downloadzone</eventCode>
        <eventDate>2025-07-30 14:30:00</eventDate>
        <eventDescription><![CDATA[Llegó al descargue]]></eventDescription>
        <idManifest>MAN-2025-001234</idManifest>
        <latitude>10.391049</latitude>
        <longitude>-75.514381</longitude>
        <location><![CDATA[Km 3 Via Mamonal Zona Industrial, Cartagena]]></location>
        <state></state>
        <velocity></velocity>
        <temperature></temperature>
      </event>
    </ser:event>
  </soapenv:Body>
</soapenv:Envelope>
```

### Ejemplo: Evento Satrack GPS (rastreo)

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.soap.soapexposer.mayasoft.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:event>
      <authToken>
        <authUser>USUARIO_MONITOR</authUser>
        <authPassword>PASSWORD_MONITOR</authPassword>
      </authToken>
      <event>
        <eventCode>speeding</eventCode>
        <eventDate>2025-07-29T15:43:46</eventDate>
        <eventDescription><![CDATA[Exceso de velocidad]]></eventDescription>
        <idManifest>MAN-2025-001234</idManifest>
        <latitude>7.159516</latitude>
        <longitude>-73.129672</longitude>
        <location><![CDATA[Autopista Bucaramanga - Bogotá Km 45]]></location>
        <state>on</state>
        <velocity>92</velocity>
        <temperature>4</temperature>
      </event>
    </ser:event>
  </soapenv:Body>
</soapenv:Envelope>
```

### Ejemplo: Evento Last Tracking (reporte manual)

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.soap.soapexposer.mayasoft.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:event>
      <authToken>
        <authUser>USUARIO_MONITOR</authUser>
        <authPassword>PASSWORD_MONITOR</authPassword>
      </authToken>
      <event>
        <eventCode>lasttracking</eventCode>
        <eventDate>2025-07-29 11:20:00</eventDate>
        <eventDescription><![CDATA[Parada por descanso del conductor]]></eventDescription>
        <idManifest>MAN-2025-001234</idManifest>
        <latitude>6.250155</latitude>
        <longitude>-75.563591</longitude>
        <location><![CDATA[Estación de servicio Terpel, Autopista Medellín Km 22]]></location>
        <state></state>
        <velocity></velocity>
        <temperature></temperature>
      </event>
    </ser:event>
  </soapenv:Body>
</soapenv:Envelope>
```

## 10. Respuesta esperada

Idéntica a todos los servicios de Monitor:

```xml
<return>
  <code>000</code>
  <description>TRANSACCION EXITOSA</description>
</return>
```

**Interpretación por LoggiApp:**

| Código                | Acción de LoggiApp                                                            |
| --------------------- | ----------------------------------------------------------------------------- |
| `000` (éxito)         | Marca el evento como transmitido (`transmited = true`).                       |
| `001` (error interno) | Se reintenta **una vez** más. Si falla de nuevo, se guarda como no transmitido.|
| Otros códigos         | Se almacena como fallido (`transmited = false`).                              |

**Persistencia del resultado según tipo:**

| Tipo de evento   | Campo persistido                                    | Almacenamiento adicional                                                                                               |
| ---------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Loadzone         | `cargo.monitorState.loadZoneEventResponse`          | —                                                                                                                      |
| Downloadzone     | `cargo.monitorState.downloadZoneEventResponse`      | Se crea registro en sub-colección `downloadZoneEvents` con: `addressId`, `destinationId`, `name`, `municipalityCode`, `address`. |
| Satrack GPS      | `cargo.monitorState.lastTrackingEventResponse`      | Se crea registro en historial `lastTrackingMonitor` con: `address`, `reportDescription`, `fingerprint`.                |
| Last Tracking    | `cargo.monitorState.lastTrackingEventResponse`      | Se crea registro en historial `lastTrackingMonitor` con: `address`, `reportDescription`, `fingerprint`.                |

## 11. Observaciones

| #  | Observación |
| -- | ----------- |
| 1  | **El servicio `event` no existe en el contrato oficial DD-EST-02.** Es un servicio adicional/personalizado que LoggiApp consume en Monitor. El contrato oficial no documenta este endpoint. |
| 2  | **Idempotencia del evento loadzone.** Si `monitorState.loadZoneEventResponse.transmited == true`, no se reenvía. |
| 3  | **Idempotencia del evento downloadzone.** Se valida por combinación de `addressId + destinationId`. Un mismo destino puede tener múltiples eventos de descarga si tiene múltiples direcciones. |
| 4  | **Los eventos Satrack se envían solo cuando hay cambio de estado.** No se reporta cada posición GPS, sino solo cuando el estado del vehículo cambia (ej: de movimiento a detenido). |
| 5  | **Los eventos Satrack sobreponen el lastTrackingEventResponse.** Cada nuevo evento Satrack o Last Tracking sobreescribe el campo `lastTrackingEventResponse`, pero se mantiene un historial separado en `lastTrackingMonitor`. |
| 6  | **Velocidad > 75 km/h siempre genera código `speeding`.** Independientemente del tipo de evento Satrack original, si la velocidad supera 75 km/h se clasifica como exceso de velocidad. |
| 7  | **Requiere manifiesto.** Todos los tipos de evento validan que `cargo.manifest` no esté vacío antes de intentar el envío. |
| 8  | **Ejecución asíncrona.** Todos los tipos de evento se ejecutan en el thread pool `monitorCargoExecutor`. |
| 9  | **El evento loadzone se ejecuta secuencialmente después del loadShipment.** Ambos comparten el mismo hilo asíncrono cuando se invocan desde `START_TRIP`, garantizando que el despacho exista en Monitor antes de enviar el evento. |
| 10 | **Los campos `state`, `velocity` y `temperature` solo se llenan para eventos Satrack.** Para los demás tipos, se envían como cadenas vacías. |
