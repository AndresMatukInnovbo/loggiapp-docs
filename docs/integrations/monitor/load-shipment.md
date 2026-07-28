# Servicio: loadShipment

## 1. Nombre

`loadShipment`

## 2. Objetivo

Este servicio **crea un despacho (shipment) en la plataforma Monitor** utilizando la información de una carga existente en LoggiApp.

El despacho incluye los datos del manifiesto de transporte, la ruta planificada, el vehículo asignado, el conductor, y las órdenes de carga (remesas) asociadas. Una vez creado en Monitor, el despacho comienza a ser monitoreado satelitalmente.

## 3. Cuándo se ejecuta

| Aspecto           | Detalle |
| ----------------- | ------- |
| **Evento**        | La carga cambia al estado `START_TRIP` (inicio de viaje) |
| **Actor**         | Conductor (desde la app móvil) o usuario web que actualiza el tracking |
| **Condición 1**   | El `holderId` debe ser `Companies.TECLOGI` |
| **Condición 2**   | El `idCompany` de la carga debe estar en `MonitorCargoCompanies` (actualmente solo Maersk Logistics) |
| **Condición 3**   | La carga NO debe haber sido registrada previamente en Monitor (`monitorState.loadShipmentResponse.transmited == false`) |
| **Condición 4**   | La carga debe tener un número de manifiesto asignado (`cargo.manifest` no vacío) |

> **Endpoint REST manual:** `POST /monitor/{cargoId}/load-shipment`  
> Permite re-ejecutar el registro de forma manual desde la interfaz web.

## 4. Flujo

```
Conductor inicia viaje (START_TRIP)
        ↓
CargoBusinessImpl.tracking(action, imagesCargoRequest)
        ↓
CargoBusinessImpl.reportToMonitorCargo("START_TRIP", cargo, holderId, ...)
        ↓
MonitorCargoBusinessImpl.registerMonitorLoadShipmentAndLoadzoneEvent(...)
        ↓  [Ejecutado en thread asíncrono: monitorCargoExecutor]
MonitorCargoBusinessImpl.registerMonitorLoadShipmentSync(...)
        ↓
¿La carga ya fue registrada en Monitor?
        ↓ NO
validateLoadShipmentBuild(cargo, user, holderId)
        ↓
¿Errores de validación?
        ↓ NO
buildLoadShipmentRequest(cargo, user, holderId, validator)
        ↓
MonitorServiceImpl.loadShipment(request, holderId)
        ↓
Se construye el SOAP envelope y se envía por HTTP POST
        ↓
Monitor procesa y responde (código 000 = éxito, 006 = ya existe)
        ↓
Se almacena el resultado en cargo.monitorState.loadShipmentResponse
```

## 5. Lugares donde se llama

| Clase                        | Método                                                    | Motivo                                                                          | Condición                                                  |
| ---------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `CargoBusinessImpl`          | `tracking(...)` → `reportToMonitorCargo(...)`             | Registrar automáticamente el despacho cuando el conductor inicia el viaje       | `action == StateCargo.START_TRIP`                           |
| `CargoServiceImpl` (REST)    | `registerMonitorLoadShipment(cargoId)`                    | Endpoint REST para registrar manualmente un despacho en Monitor                 | Invocación directa: `POST /monitor/{cargoId}/load-shipment`|
| `MonitorCargoBusinessImpl`   | `registerMonitorLoadShipmentAndLoadzoneEvent(...)`         | Método compuesto: loadShipment + evento zona de carga secuencialmente           | Llamado desde `reportToMonitorCargo` con `START_TRIP`      |
| `MonitorCargoBusinessImpl`   | `registerMonitorLoadShipment(...)`                         | Versión independiente que solo ejecuta loadShipment                             | Llamado desde el endpoint REST manual                      |

## 6. Datos enviados a Monitor

### Manifest (Datos del manifiesto)

| Campo LoggiApp                                    | Campo Monitor         | Descripción                                           | Obligatorio | Fuente                                                                    |
| ------------------------------------------------- | --------------------- | ----------------------------------------------------- | :---------: | ------------------------------------------------------------------------- |
| `cargo.manifest`                                  | `idManifest`          | Número del manifiesto de transporte                   | Sí          | `Cargo.manifest`                                                          |
| `cargo.expeditionManifest`                        | `createmanifestdate`  | Fecha de creación/expedición del manifiesto           | Sí          | `Cargo.expeditionManifest` → formato `yyyy-MM-dd HH:mm:ss`               |
| `cargo.startTripDate`                             | `departureTime`       | Fecha de salida del vehículo                          | Sí          | `Cargo.startTripDate` → hora colombiana `yyyy-MM-dd HH:mm:ss`            |
| `cargo.cargoModel.operationType.description`      | `operationType`       | Tipo de operación (NACIONAL, URBANO, etc.)            | Sí          | `Cargo.cargoModel.operationType.description`                              |
| `cargo.observation`                               | `observation`         | Observaciones de la carga                             | No          | `Cargo.observation`                                                       |

### Generator (Generador / Dueño de la carga)

| Campo LoggiApp                        | Campo Monitor     | Descripción                                                  | Obligatorio | Fuente                           |
| ------------------------------------- | ----------------- | ------------------------------------------------------------ | :---------: | -------------------------------- |
| `cargo.cargoOwner.documentNumber`     | `idGenerator`     | NIT del generador (sin dígito de verificación si es NIT)     | Sí          | `Cargo.cargoOwner.documentNumber`|
| `cargo.cargoOwner.name`               | `nameGenerator`   | Nombre del generador de la carga                             | Sí          | `Cargo.cargoOwner.name`          |

### Transporter (Transportador)

| Campo LoggiApp                    | Campo Monitor       | Descripción                                                     | Obligatorio | Fuente                             |
| --------------------------------- | ------------------- | --------------------------------------------------------------- | :---------: | ---------------------------------- |
| `companySaas.transportCompanyId`  | `idTransporter`     | NIT de la empresa transportadora (sin dígito de verificación)   | Sí          | `CompanySAAS.transportCompanyId`   |
| `companySaas.name`                | `nameTransporter`   | Nombre de la empresa transportadora                             | Sí          | `CompanySAAS.name`                 |

### RoutePlane (Plan de ruta)

| Campo LoggiApp                    | Campo Monitor               | Descripción                       | Obligatorio | Fuente                          |
| --------------------------------- | --------------------------- | --------------------------------- | :---------: | ------------------------------- |
| `itinerary.name`                  | `routeName`                 | Nombre de la ruta (itinerario)    | Sí          | `Itinerary.name`                |
| `itinerary.name`                  | `via`                       | Vía (mismo nombre del itinerario) | Sí          | `Itinerary.name`                |
| `itinerary.originPoint.id`        | `origin.idOrigen`           | Código DANE del municipio origen  | Sí          | `Itinerary.originPoint.id`      |
| `itinerary.destinationPoint.id`   | `destination.idDestination` | Código DANE del municipio destino | Sí          | `Itinerary.destinationPoint.id` |

### Vehicle (Vehículo)

| Campo LoggiApp       | Campo Monitor   | Descripción          | Obligatorio | Fuente             |
| -------------------- | --------------- | -------------------- | :---------: | ------------------ |
| `cargo.licensePlate` | `licensePlate`  | Placa del vehículo   | Sí          | `Cargo.licensePlate`|

### Driver (Conductor)

| Campo LoggiApp                          | Campo Monitor  | Descripción                   | Obligatorio | Fuente                                              |
| --------------------------------------- | -------------- | ----------------------------- | :---------: | --------------------------------------------------- |
| `user.information.document`             | `id`           | Cédula/documento del conductor| Sí          | `User.information.document`                         |
| `user.information.name` (primer nombre) | `name`         | Primer nombre del conductor   | Sí          | `User.information.name` → `Utils.returnNames()`     |
| `user.information.name` (primer apellido)| `surname`     | Primer apellido del conductor | Sí          | `User.information.name` → `Utils.returnNames()`     |
| `user.phone`                            | `mobilNumber`  | Celular del conductor         | Sí          | `User.phone`                                        |

### LoadingOrders / Remittances (Órdenes de carga)

Se envía una remesa por cada `Consignment` asociado a la carga (en estado `CREATED`).

| Campo LoggiApp                                                     | Campo Monitor                  | Descripción                                          | Obligatorio | Fuente                                                      |
| ------------------------------------------------------------------ | ------------------------------ | ---------------------------------------------------- | :---------: | ----------------------------------------------------------- |
| `cargo.consecutive` + `"_"` + `consignment.id`                    | `idCargo`                      | Identificador único de la orden de carga             | Sí          | Concatenación `Cargo.consecutive` + "_" + `Consignment.id`  |
| `consignment.id`                                                   | `remittancenumber`             | Número de la remesa                                  | Sí          | `Consignment.id`                                            |
| `consignment.load.date` + `consignment.load.appointmentTime`      | `appointment`                  | Cita de carga (fecha + hora combinadas)              | Sí          | `Consignment.load.date` + `.appointmentTime`                |
| `consignment.unload.date` + `consignment.unload.appointmentTime`  | `estimatedDeliveryDate`        | Cita de descarga (fecha + hora combinadas)           | Sí          | `Consignment.unload.date` + `.appointmentTime`              |
| `cargo.cargoOwner.documentNumber`                                  | `generador.idGenerator`        | NIT del generador (mismo del manifest)               | Sí          | `Cargo.cargoOwner.documentNumber`                           |
| `cargo.cargoOwner.name`                                            | `generador.nameGenerator`      | Nombre del generador (mismo del manifest)            | Sí          | `Cargo.cargoOwner.name`                                     |
| `consignment.sender.documentNumber`                                | `sender.idSender`              | NIT del remitente (sin dígito si es NIT)             | Sí          | `Consignment.sender.documentNumber`                         |
| `consignment.sender.name`                                          | `sender.nameSender`            | Nombre del remitente                                 | Sí          | `Consignment.sender.name`                                   |
| `consignment.recipient.documentNumber`                             | `receiver.idReceiver`          | NIT del destinatario (sin dígito si es NIT)          | Sí          | `Consignment.recipient.documentNumber`                      |
| `consignment.recipient.name`                                       | `receiver.nameReceiver`        | Nombre del destinatario                              | Sí          | `Consignment.recipient.name`                                |
| `consignment.sender.municipalityCode`                              | `origin.idOrigen`              | Código DANE del municipio de cargue                  | Sí          | `Consignment.sender.municipalityCode`                       |
| `consignment.sender.address`                                       | `origin.originAddress`         | Dirección del punto de cargue                        | Sí          | `Consignment.sender.address`                                |
| `consignment.recipient.municipalityCode`                           | `destination.idDestination`    | Código DANE del municipio de descargue               | Sí          | `Consignment.recipient.municipalityCode`                    |
| `consignment.recipient.address`                                    | `destination.destinationAddress`| Dirección del punto de descargue                    | Sí          | `Consignment.recipient.address`                             |
| _(fijo: "INLAND")_                                                 | `referenceNumber`              | Número de referencia                                 | Sí          | Valor fijo hardcodeado                                      |
| `cargo.container`                                                  | `container`                    | Número de contenedor                                 | No          | `Cargo.container` (null si está vacío)                      |
| `cargo.riskProfile.id` _(transformado)_                            | `merchandise.category`         | Categoría de la carga (A, B, C, D)                   | Sí          | `Cargo.riskProfile.id` → 1=A, 2=B, 3=C, default=A          |
| `consignment.merchandise.description`                              | `merchandise.productName`      | Nombre del producto de carga                         | Sí          | `Consignment.merchandise.description`                       |

## 7. Campos de Monitor NO utilizados por LoggiApp

Los siguientes campos existen en el contrato oficial de Monitor pero LoggiApp **actualmente NO los envía**:

??? info "Manifest"

    - `submittedmanifest` (radicado RNDC)
    - `dispatcher.id`, `dispatcher.name`, `dispatcher.email` (datos del despachador)
    - `agency.id`, `agency.name` (agencia que despacha)
    - `generador.emailGenerator`, `generador.phoneNumberGenerator`
    - `transporter.emailTransporter`, `transporter.phoneNumberTransporter`
    - `vehicleOwner.id`, `vehicleOwner.typeId`, `vehicleOwner.email`, `vehicleOwner.name`, `vehicleOwner.phoneNumber`

??? info "RoutePlane"

    - `origin.originCity`, `origin.originDepartment`, `origin.origenLatitude`, `origin.origenLongitude`, `origin.originAddress` (a nivel ruta)
    - `destination.destinationCity`, `destination.destinationDepartment`, `destination.destinationLatitude`, `destination.destinationLongitude`, `destination.destinationAddress` (a nivel ruta)
    - `extraPoints` (puntos intermedios / zonas de control)

??? info "Vehicle"

    - `color`, `model`, `vehicleMake`, `vehicleBody`, `ownerType`, `trailerNumber`
    - `vehicleClass`, `capacity`, `length`, `width`, `height`, `emptyWeight`, `maximumWeight`
    - `image` (imagen del vehículo)

??? info "Driver"

    - `phoneNumber` (teléfono fijo)
    - `address`
    - `emailDriver`
    - `image` (foto del conductor)

??? info "GPS Provider"

    - `gpsProvider.id`, `gpsProvider.user`, `gpsProvider.password`, `gpsProvider.idCompany` (proveedor satelital principal)
    - Toda la sección de `gpsSecuntaryProviders` (candados, escolta, termocupla)

??? info "Remittance (Órdenes de carga)"

    - `orderNumber` (número del pedido)
    - `shippingGuide` (guía de envío)
    - `bl` (bill of lading)
    - `shippingline`, `containerowner`, `containertype`, `containersize`
    - `sector`, `dtaformdate`, `dtaexpirationdate`
    - `generador.emailGenerator`, `generador.phoneNumberGenerator`
    - `sender.emailSender`, `sender.phoneNumberSender`
    - `receiver.emailReceiver`, `receiver.phoneNumberReceiver`
    - `origin.originCity`, `origin.originDepartment`, `origin.originLatidude`, `origin.originLongitude`
    - `destination.destinationCity`, `destination.destinationDepartment`, `destination.destinationLatidude`, `destination.destinationLongitude`
    - Tiempos logísticos en la remesa (`arrivaldownloadsitetime`, `arrivalloadsite`, `enddownloadtime`, `endloadtime`)
    - `merchandise.observations`, `merchandise.merchandisevalue`, `merchandise.merchandisetype`
    - `documents` (lista de documentos solicitados al conductor)

## 8. Transformaciones

| Transformación                          | Descripción                                                                                                                                                                                                   |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **NIT sin dígito de verificación**      | Si el tipo de documento es NIT, se remueve el dígito de verificación usando `Utils.nitWithoutDigit()`. Aplica a: generador, transportador, remitente y destinatario.                                          |
| **Nombre del conductor**                | El nombre completo del conductor se descompone usando `Utils.returnNames()` para extraer `firstName` y `firstSurname` por separado.                                                                           |
| **Fecha de expedición del manifiesto**  | Se convierte del formato interno `yyyy-MM-dd HH:mm` al formato requerido `yyyy-MM-dd HH:mm:ss`.                                                                                                              |
| **Fecha de salida**                     | Se convierte de `Date` a String en zona horaria colombiana con formato `yyyy-MM-dd HH:mm:ss`.                                                                                                                 |
| **Citas de carga y descarga**           | Se combinan `date` + `appointmentTime` del consignment en un solo String con formato `yyyy-MM-dd HH:mm:ss`.                                                                                                   |
| **idCargo de la remesa**                | Se construye como: `cargo.consecutive` + "_" + `consignment.id` (ej: `1234_CON001`).                                                                                                                         |
| **routeName y via**                     | Ambos campos se asignan con el mismo valor: `itinerary.name`.                                                                                                                                                 |
| **referenceNumber**                     | Siempre se envía el valor fijo `"INLAND"`.                                                                                                                                                                    |
| **Categoría de mercancía**              | Se mapea el `riskProfile.id` del cargo: `1` → `A`, `2` → `B`, `3` → `C`, cualquier otro o null → `A`.                                                                                                       |
| **Contenedor**                          | Si `cargo.container` está vacío o nulo, se envía `null` (no se incluye en el XML).                                                                                                                            |
| **CDATA wrapping**                      | Después de la conversión a XML, los campos de texto (`operationType`, `nameGenerator`, `nameTransporter`, `routeName`, `via`, `name`, `surname`, `nameSender`, `nameReceiver`, `originAddress`, `destinationAddress`, `productName`, `observation`) se envuelven en `<![CDATA[...]]>` para prevenir problemas con caracteres especiales. |

## 9. Request construido

Ejemplo del request SOAP que genera LoggiApp (con datos ficticios respetando la estructura real del código):

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.soap.soapexposer.mayasoft.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:loadShipment>
      <authToken>
        <authUser>USUARIO_MONITOR</authUser>
        <authPassword>PASSWORD_MONITOR</authPassword>
      </authToken>
      <manifest>
        <idManifest>MAN-2025-001234</idManifest>
        <createmanifestdate>2025-07-28 08:30:00</createmanifestdate>
        <departureTime>2025-07-28 09:00:00</departureTime>
        <operationType><![CDATA[NACIONAL]]></operationType>
        <observation>Carga refrigerada - manejar con cuidado</observation>
        <generador>
          <idGenerator>900123456</idGenerator>
          <nameGenerator><![CDATA[EMPRESA GENERADORA S.A.S]]></nameGenerator>
        </generador>
        <transporter>
          <idTransporter>800987654</idTransporter>
          <nameTransporter><![CDATA[TRANSPORTES EJEMPLO S.A]]></nameTransporter>
        </transporter>
      </manifest>
      <routePlane>
        <routeName><![CDATA[Bogotá - Cartagena Nacional]]></routeName>
        <via><![CDATA[Bogotá - Cartagena Nacional]]></via>
        <origin>
          <idOrigen>11001000</idOrigen>
        </origin>
        <destination>
          <idDestination>13001000</idDestination>
        </destination>
      </routePlane>
      <vehicle>
        <licensePlate>ABC123</licensePlate>
      </vehicle>
      <driver>
        <id>1098765432</id>
        <name><![CDATA[CARLOS]]></name>
        <surname><![CDATA[RODRIGUEZ PEREZ]]></surname>
        <mobilNumber>3101234567</mobilNumber>
      </driver>
      <loadingOrders>
        <remittance>
          <idCargo>5678_CON-001</idCargo>
          <remittancenumber>CON-001</remittancenumber>
          <referenceNumber>INLAND</referenceNumber>
          <appointment>2025-07-28 10:00:00</appointment>
          <estimatedDeliveryDate>2025-07-30 14:00:00</estimatedDeliveryDate>
          <container>MSKU1234567</container>
          <generador>
            <idGenerator>900123456</idGenerator>
            <nameGenerator><![CDATA[EMPRESA GENERADORA S.A.S]]></nameGenerator>
          </generador>
          <sender>
            <idSender>800111222</idSender>
            <nameSender><![CDATA[BODEGA ORIGEN LTDA]]></nameSender>
          </sender>
          <receiver>
            <idReceiver>800333444</idReceiver>
            <nameReceiver><![CDATA[ALMACEN DESTINO S.A]]></nameReceiver>
          </receiver>
          <origin>
            <idOrigen>11001000</idOrigen>
            <originAddress><![CDATA[Calle 80 #45-23 Bodega 5]]></originAddress>
          </origin>
          <destination>
            <idDestination>13001000</idDestination>
            <destinationAddress><![CDATA[Km 3 Via Mamonal Zona Industrial]]></destinationAddress>
          </destination>
          <merchandise>
            <category>A</category>
            <productName><![CDATA[QUIMICOS INDUSTRIALES]]></productName>
          </merchandise>
        </remittance>
      </loadingOrders>
    </ser:loadShipment>
  </soapenv:Body>
</soapenv:Envelope>
```

## 10. Respuesta esperada

Monitor devuelve un XML SOAP con un elemento `<return>`:

```xml
<return>
  <code>000</code>
  <description>TRANSACCION EXITOSA</description>
</return>
```

**Interpretación por LoggiApp:**

| Código              | Acción de LoggiApp                                                                                    |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| `000` (éxito)       | Marca `monitorState.loadShipmentResponse.transmited = true`. La carga se considera registrada.        |
| `006` (ya existe)   | También se considera como registro exitoso (`transmited = true`). No genera error.                    |
| `001` (error interno)| Se reintenta **una vez** más. Si falla nuevamente, se guarda como no transmitido.                    |
| Otros códigos       | Se almacena el código y descripción como respuesta fallida (`transmited = false`).                    |

**Persistencia del resultado:**

El resultado se almacena en `cargo.monitorState.loadShipmentResponse`:

- `code`: Código de respuesta de Monitor
- `description`: Descripción de la respuesta
- `transmited`: `true` si fue exitoso (código 000 o 006), `false` en cualquier otro caso
- `errors`: Lista de errores de validación (si los hubo antes de enviar)

## 11. Observaciones

| #  | Observación |
| -- | ----------- |
| 1  | **Solo se ejecuta si existe manifiesto.** La validación verifica que `cargo.manifest` no sea vacío antes de intentar el envío. |
| 2  | **Idempotencia.** Si la carga ya fue registrada (`monitorState.loadShipmentResponse.transmited == true`), la operación se aborta sin enviar. |
| 3  | **Reintento automático.** Si Monitor responde con error interno (código `001`), se reintenta una vez más antes de guardar el fallo. |
| 4  | **Solo Maersk Logistics.** Actualmente la integración está habilitada exclusivamente para la empresa con NIT `83008063410` (Maersk Logistics). |
| 5  | **Solo holder Teclogi.** El `holderId` debe ser el valor de `Companies.TECLOGI`. |
| 6  | **Ejecución asíncrona.** El envío se realiza en un thread separado (`monitorCargoExecutor`). No bloquea la respuesta al usuario. |
| 7  | **Validación previa exhaustiva.** Antes de construir el request, se validan todos los campos requeridos. Si falla la validación, se almacena el error sin intentar la conexión a Monitor. |
| 8  | **Solo remesas en estado CREATED.** Se envían únicamente los consignments cuyo estado sea `CREATED`. |
| 9  | **Se ejecuta junto con el evento de zona de carga.** Cuando se invoca desde `START_TRIP`, inmediatamente después del loadShipment se ejecuta también el registro del evento de zona de carga (loadzone event). |
| 10 | **No se envían datos del GPS ni proveedor satelital.** A pesar de que el contrato de Monitor lo permite, LoggiApp no envía información del proveedor GPS. |
| 11 | **Solo se envía la placa del vehículo.** No se envían marca, color, modelo, carrocería ni demás datos del vehículo que Monitor acepta. |
