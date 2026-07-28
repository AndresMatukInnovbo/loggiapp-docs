# Integración LoggiApp — Monitor

> **Versión:** 1.0  
> **Última actualización:** Julio 2026  
> **Fuente de verdad:** Código fuente de LoggiApp  
> **Contrato de referencia:** DD-EST-02 — WS Proveedor Integración TMS hacia Monitor Tiempos RNDC

---

## Tabla de contenido

- [Introducción](#introducción)
- [Arquitectura](#arquitectura)
- [Servicios implementados en LoggiApp](#servicios-documentados-implementados-en-loggiapp)
- [Servicios NO implementados (gap vs. contrato oficial)](#servicios-del-contrato-oficial-no-implementados-en-loggiapp)
- [Servicio: loadShipment](#servicio-loadshipment)
- [Servicio: event](#servicio-event)
- [Servicio: image](#servicio-image)
- [Servicio: finalizeShipment](#servicio-finalizeshipment)
- [Servicio: cancelShipment](#servicio-cancelshipment)

---

## Introducción

Este documento describe la integración técnica y funcional entre **LoggiApp** (plataforma TMS de Teclogi) y **Monitor** (plataforma de monitoreo satelital de MayaSoft).

La integración se realiza mediante servicios web SOAP expuestos por Monitor. LoggiApp actúa como **consumidor** de estos servicios, enviando información sobre despachos, eventos de rastreo, y cambios de estado de las cargas en tiempo real.

### Alcance

Este documento refleja **exclusivamente** lo que el código fuente de LoggiApp implementa actualmente. No es una copia del manual oficial de Monitor. Si existe una diferencia entre el contrato oficial y el código, se documenta lo que realmente hace el código.

### Audiencia

- Clientes que desean evaluar si la integración actual cubre sus necesidades.
- Integradores y arquitectos que requieran entender los flujos técnicos.
- Desarrolladores que mantengan o extiendan la integración.

---

## Arquitectura

### Protocolo de comunicación

| Aspecto          | Detalle                                                         |
| ---------------- | --------------------------------------------------------------- |
| Protocolo        | SOAP sobre HTTP/HTTPS                                           |
| Método HTTP      | POST                                                            |
| Content-Type     | `text/xml; charset=utf-8`                                       |
| Namespace SOAP   | `http://service.soap.soapexposer.mayasoft.com/`                 |
| URL Producción   | Configurada en `monitor.soap.prod` (properties)                 |
| URL Desarrollo   | `https://monitorpiloto.mayasoft.ai/soap/ws/LoadShipment?wsdl`   |

### Componentes principales

```
┌─────────────────────┐         SOAP/HTTP          ┌──────────────────┐
│     LoggiApp        │ ─────────────────────────►  │     Monitor      │
│                     │                             │   (MayaSoft)     │
│  MonitorCargoBusi-  │  LoadShipmentRequest        │                  │
│  nessImpl           │  EventRequest               │  Recibe y        │
│       ↓             │  FinalizeShipmentRequest    │  monitorea       │
│  MonitorServiceImpl │  CancelShipmentRequest      │  despachos       │
│       ↓             │  ImageRequest               │                  │
│  HTTP Connection    │ ◄───────────────────────── │  MonitorResponse │
└─────────────────────┘                             └──────────────────┘
```

### Autenticación

| Ambiente     | Mecanismo                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------- |
| Producción   | Credenciales almacenadas en base de datos (`CompanySAAS.integrationCredentials`) por empresa (holder), canal `MONITOR_CARGO`. |
| Desarrollo   | Credenciales hardcodeadas: usuario `PILOTO`, contraseña `PILOTO`.                                 |

### Ejecución asíncrona

Todas las operaciones de integración con Monitor se ejecutan de forma **asíncrona** usando un thread pool dedicado (`monitorCargoExecutor`) mediante la anotación `@Async`. Esto garantiza que una falla en Monitor no bloquee el flujo principal de la aplicación.

### Restricción de empresas

La integración **solo se activa** para empresas que cumplan ambas condiciones:

1. El `holderId` sea igual a `Companies.TECLOGI` (la plataforma Teclogi).
2. El `idCompany` de la carga esté registrado en `MonitorCargoCompanies` (actualmente solo **Maersk Logistics** — NIT: `83008063410`).

### Respuesta estándar de Monitor

| Código | Descripción              | Significado                             |
| ------ | ------------------------ | --------------------------------------- |
| 000    | TRANSACCION EXITOSA      | Operación procesada correctamente       |
| 001    | ERROR INTERNO            | Error no controlado en Monitor          |
| 002    | PARAMETRO OBLIGATORIO    | Falta un campo requerido                |
| 003    | FORMATO NO VALIDO        | Valor con formato incorrecto            |
| 004    | CREDENCIALES INVALIDAS   | Usuario/contraseña incorrectos          |
| 005    | VALOR FUERA DE RANGO     | Campo excede longitud permitida         |
| 006    | DESPACHO YA EXISTE       | El despacho ya fue creado previamente   |

---

## Servicios documentados (implementados en LoggiApp)

| #   | Servicio                                            | Estado en LoggiApp                          |
| --- | --------------------------------------------------- | ------------------------------------------- |
| 1   | [loadShipment](#servicio-loadshipment)              | Activo                                      |
| 2   | [event](#servicio-event)                            | Activo                                      |
| 3   | [image](#servicio-image)                            | Implementado pero NO activo (sin callers)   |
| 4   | [finalizeShipment](#servicio-finalizeshipment)      | Activo                                      |
| 5   | [cancelShipment](#servicio-cancelshipment)          | Activo                                      |

---

## Servicios del contrato oficial NO implementados en LoggiApp

Los siguientes servicios están definidos en el contrato oficial de Monitor (DD-EST-02) pero **LoggiApp no los implementa actualmente**. No existe código, DTOs, ni lógica de negocio para ninguno de ellos.

| #   | Servicio Monitor            | Propósito según contrato oficial | Impacto de no tenerlo |
| --- | --------------------------- | -------------------------------- | --------------------- |
| 1   | `updateShipment`            | Actualizar un despacho ya creado en Monitor. Permite modificar datos del manifiesto, ruta, vehículo, conductor y órdenes de carga después de la creación inicial. | Si los datos de un despacho cambian después del inicio del viaje (ej: cambio de conductor, cambio de ruta, corrección de datos), Monitor no se entera. La información queda desactualizada. |
| 2   | `upsertCargo`               | Insertar o actualizar una orden de carga (remesa) individual, sin necesidad de enviar todo el despacho. Permite agregar remesas nuevas a un despacho existente o modificar las existentes. | No se pueden agregar remesas a un despacho ya creado en Monitor. Todas las remesas deben existir al momento del `loadShipment`. |
| 3   | `cancelCargo`               | Cancelar o eliminar una orden de carga (remesa) individual dentro de un despacho. Permite marcar una remesa como cancelada sin afectar el despacho completo. | Si una remesa se cancela en LoggiApp, Monitor sigue mostrándola como activa. Solo se puede cancelar el despacho completo (`cancelShipment`), no remesas individuales. |
| 4   | `logisticTime`              | Subir tiempos logísticos detallados a una orden de carga: llegada al sitio de cargue, inicio de cargue, fin de cargue, salida del sitio de cargue, llegada al sitio de descargue, inicio de descargue, fin de descargue. | Monitor no recibe los tiempos logísticos reales de cargue/descargue. Solo recibe el evento de "llegada" (vía `event`), pero no los tiempos de inicio/fin de las operaciones de carga y descarga. |
| 5   | `updateSubmittedmanifest`   | Actualizar el número de radicado del manifiesto ante el RNDC (Registro Nacional de Despachos de Carga). Permite informar a Monitor el número asignado por el ministerio después de la radicación. | Monitor no recibe el número de radicado RNDC. Si el cliente requiere que Monitor muestre el radicado del manifiesto, esta información no se sincroniza. |

### Resumen de cobertura

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

---

## Servicio: loadShipment

### 1. Nombre

`loadShipment`

### 2. Objetivo

Este servicio **crea un despacho (shipment) en la plataforma Monitor** utilizando la información de una carga existente en LoggiApp.

El despacho incluye los datos del manifiesto de transporte, la ruta planificada, el vehículo asignado, el conductor, y las órdenes de carga (remesas) asociadas. Una vez creado en Monitor, el despacho comienza a ser monitoreado satelitalmente.

### 3. Cuándo se ejecuta

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

### 4. Flujo

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

### 5. Lugares donde se llama

| Clase                        | Método                                                    | Motivo                                                                          | Condición                                                  |
| ---------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `CargoBusinessImpl`          | `tracking(...)` → `reportToMonitorCargo(...)`             | Registrar automáticamente el despacho cuando el conductor inicia el viaje       | `action == StateCargo.START_TRIP`                           |
| `CargoServiceImpl` (REST)    | `registerMonitorLoadShipment(cargoId)`                    | Endpoint REST para registrar manualmente un despacho en Monitor                 | Invocación directa: `POST /monitor/{cargoId}/load-shipment`|
| `MonitorCargoBusinessImpl`   | `registerMonitorLoadShipmentAndLoadzoneEvent(...)`         | Método compuesto: loadShipment + evento zona de carga secuencialmente           | Llamado desde `reportToMonitorCargo` con `START_TRIP`      |
| `MonitorCargoBusinessImpl`   | `registerMonitorLoadShipment(...)`                         | Versión independiente que solo ejecuta loadShipment                             | Llamado desde el endpoint REST manual                      |

### 6. Datos enviados a Monitor

#### Manifest (Datos del manifiesto)

| Campo LoggiApp                                    | Campo Monitor         | Descripción                                           | Obligatorio | Fuente                                                                    |
| ------------------------------------------------- | --------------------- | ----------------------------------------------------- | :---------: | ------------------------------------------------------------------------- |
| `cargo.manifest`                                  | `idManifest`          | Número del manifiesto de transporte                   | Sí          | `Cargo.manifest`                                                          |
| `cargo.expeditionManifest`                        | `createmanifestdate`  | Fecha de creación/expedición del manifiesto           | Sí          | `Cargo.expeditionManifest` → formato `yyyy-MM-dd HH:mm:ss`               |
| `cargo.startTripDate`                             | `departureTime`       | Fecha de salida del vehículo                          | Sí          | `Cargo.startTripDate` → hora colombiana `yyyy-MM-dd HH:mm:ss`            |
| `cargo.cargoModel.operationType.description`      | `operationType`       | Tipo de operación (NACIONAL, URBANO, etc.)            | Sí          | `Cargo.cargoModel.operationType.description`                              |
| `cargo.observation`                               | `observation`         | Observaciones de la carga                             | No          | `Cargo.observation`                                                       |

#### Generator (Generador / Dueño de la carga)

| Campo LoggiApp                        | Campo Monitor     | Descripción                                                  | Obligatorio | Fuente                           |
| ------------------------------------- | ----------------- | ------------------------------------------------------------ | :---------: | -------------------------------- |
| `cargo.cargoOwner.documentNumber`     | `idGenerator`     | NIT del generador (sin dígito de verificación si es NIT)     | Sí          | `Cargo.cargoOwner.documentNumber`|
| `cargo.cargoOwner.name`               | `nameGenerator`   | Nombre del generador de la carga                             | Sí          | `Cargo.cargoOwner.name`          |

#### Transporter (Transportador)

| Campo LoggiApp                    | Campo Monitor       | Descripción                                                     | Obligatorio | Fuente                             |
| --------------------------------- | ------------------- | --------------------------------------------------------------- | :---------: | ---------------------------------- |
| `companySaas.transportCompanyId`  | `idTransporter`     | NIT de la empresa transportadora (sin dígito de verificación)   | Sí          | `CompanySAAS.transportCompanyId`   |
| `companySaas.name`                | `nameTransporter`   | Nombre de la empresa transportadora                             | Sí          | `CompanySAAS.name`                 |

#### RoutePlane (Plan de ruta)

| Campo LoggiApp                    | Campo Monitor               | Descripción                       | Obligatorio | Fuente                          |
| --------------------------------- | --------------------------- | --------------------------------- | :---------: | ------------------------------- |
| `itinerary.name`                  | `routeName`                 | Nombre de la ruta (itinerario)    | Sí          | `Itinerary.name`                |
| `itinerary.name`                  | `via`                       | Vía (mismo nombre del itinerario) | Sí          | `Itinerary.name`                |
| `itinerary.originPoint.id`        | `origin.idOrigen`           | Código DANE del municipio origen  | Sí          | `Itinerary.originPoint.id`      |
| `itinerary.destinationPoint.id`   | `destination.idDestination` | Código DANE del municipio destino | Sí          | `Itinerary.destinationPoint.id` |

#### Vehicle (Vehículo)

| Campo LoggiApp       | Campo Monitor   | Descripción          | Obligatorio | Fuente             |
| -------------------- | --------------- | -------------------- | :---------: | ------------------ |
| `cargo.licensePlate` | `licensePlate`  | Placa del vehículo   | Sí          | `Cargo.licensePlate`|

#### Driver (Conductor)

| Campo LoggiApp                          | Campo Monitor  | Descripción                   | Obligatorio | Fuente                                              |
| --------------------------------------- | -------------- | ----------------------------- | :---------: | --------------------------------------------------- |
| `user.information.document`             | `id`           | Cédula/documento del conductor| Sí          | `User.information.document`                         |
| `user.information.name` (primer nombre) | `name`         | Primer nombre del conductor   | Sí          | `User.information.name` → `Utils.returnNames()`     |
| `user.information.name` (primer apellido)| `surname`     | Primer apellido del conductor | Sí          | `User.information.name` → `Utils.returnNames()`     |
| `user.phone`                            | `mobilNumber`  | Celular del conductor         | Sí          | `User.phone`                                        |

#### LoadingOrders / Remittances (Órdenes de carga)

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

### 7. Campos de Monitor NO utilizados por LoggiApp

Los siguientes campos existen en el contrato oficial de Monitor pero LoggiApp **actualmente NO los envía**:

<details>
<summary><strong>Manifest</strong></summary>

- `submittedmanifest` (radicado RNDC)
- `dispatcher.id`, `dispatcher.name`, `dispatcher.email` (datos del despachador)
- `agency.id`, `agency.name` (agencia que despacha)
- `generador.emailGenerator`, `generador.phoneNumberGenerator`
- `transporter.emailTransporter`, `transporter.phoneNumberTransporter`
- `vehicleOwner.id`, `vehicleOwner.typeId`, `vehicleOwner.email`, `vehicleOwner.name`, `vehicleOwner.phoneNumber`
</details>

<details>
<summary><strong>RoutePlane</strong></summary>

- `origin.originCity`, `origin.originDepartment`, `origin.origenLatitude`, `origin.origenLongitude`, `origin.originAddress` (a nivel ruta)
- `destination.destinationCity`, `destination.destinationDepartment`, `destination.destinationLatitude`, `destination.destinationLongitude`, `destination.destinationAddress` (a nivel ruta)
- `extraPoints` (puntos intermedios / zonas de control)
</details>

<details>
<summary><strong>Vehicle</strong></summary>

- `color`, `model`, `vehicleMake`, `vehicleBody`, `ownerType`, `trailerNumber`
- `vehicleClass`, `capacity`, `length`, `width`, `height`, `emptyWeight`, `maximumWeight`
- `image` (imagen del vehículo)
</details>

<details>
<summary><strong>Driver</strong></summary>

- `phoneNumber` (teléfono fijo)
- `address`
- `emailDriver`
- `image` (foto del conductor)
</details>

<details>
<summary><strong>GPS Provider</strong></summary>

- `gpsProvider.id`, `gpsProvider.user`, `gpsProvider.password`, `gpsProvider.idCompany` (proveedor satelital principal)
- Toda la sección de `gpsSecuntaryProviders` (candados, escolta, termocupla)
</details>

<details>
<summary><strong>Remittance (Órdenes de carga)</strong></summary>

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
</details>

### 8. Transformaciones

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

### 9. Request construido

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

### 10. Respuesta esperada

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

### 11. Observaciones

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

---

## Servicio: event

### 1. Nombre

`event`

### 2. Objetivo

Este servicio **reporta eventos de rastreo y monitoreo a la plataforma Monitor** asociados a un despacho activo. Permite informar a Monitor sobre:

- **Llegada al sitio de carga** (zona de cargue)
- **Llegada al sitio de descarga** (zona de descargue)
- **Posición GPS del vehículo** (rastreo satelital desde Satrack)
- **Reportes manuales de ubicación/anomalía** (registrados por el conductor o controlador)

Monitor utiliza estos eventos para alimentar su sistema de monitoreo en tiempo real, permitiendo al controlador visualizar la ubicación, velocidad, alertas y estado del vehículo durante el viaje.

### 3. Cuándo se ejecuta

El servicio `event` se invoca en **cuatro escenarios** diferentes:

| Escenario                          | Evento                                                          | Actor                    | Condición                                                                                                                  |
| ---------------------------------- | --------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **Loadzone (zona de carga)**       | La carga cambia a estado `START_TRIP`                           | Conductor / Sistema      | Se ejecuta inmediatamente después del `loadShipment`. Requiere que `durationTime.startDate` esté registrada.               |
| **Downloadzone (zona de descarga)**| La carga cambia a estado `DESTINATION_ARRIVED`                  | Conductor                | Se activa cuando el conductor reporta la llegada a un punto de destino específico (`addressId` + `destinationId`).         |
| **Satrack GPS (rastreo satelital)**| Se recibe un evento GPS de Satrack con cambio de estado         | Sistema (automático)     | Proceso de polling de Satrack detecta evento con coordenadas válidas y hay un cambio de estado del vehículo.               |
| **Last Tracking (reporte manual)** | Un conductor o controlador registra un punto de trazabilidad    | Conductor / Controlador  | Se ejecuta cuando se registra un `TracePoint` manualmente en el sistema.                                                   |

### 4. Flujo

#### Flujo Loadzone (Zona de carga)

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

#### Flujo Downloadzone (Zona de descarga)

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

#### Flujo Satrack GPS (Rastreo satelital)

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

#### Flujo Last Tracking (Reporte manual)

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

### 5. Lugares donde se llama

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

### 6. Datos enviados a Monitor

#### Estructura común a todos los eventos

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

#### Códigos de evento utilizados por LoggiApp

| Código Monitor   | Constante                       | Cuándo se usa                                                               |
| ---------------- | ------------------------------- | --------------------------------------------------------------------------- |
| `loadzone`       | `MonitorEventType.LOADZONE`     | Llegada al sitio de cargue                                                  |
| `downloadzone`   | `MonitorEventType.DOWNLOADZONE` | Llegada al sitio de descargue                                               |
| `lastgps`        | `MonitorEventType.LAST_GPS`     | Reporte GPS de Satrack (por defecto)                                        |
| `lasttracking`   | `MonitorEventType.LASTTRACKING` | Reporte manual de ubicación/anomalía                                        |
| `speeding`       | `MonitorEventType.SPEEDING`     | Exceso de velocidad (Satrack evento 24, o velocidad > 75 km/h)              |
| `badgps`         | `MonitorEventType.BAD_GPS`      | Desconexión de antena GPS (Satrack evento 27)                               |
| `deviation`      | `MonitorEventType.DEVIATION`    | Giro repentino / desviación de ruta (Satrack evento 600)                    |

#### Detalle por tipo de evento

##### Evento Loadzone (zona de carga)

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

##### Evento Downloadzone (zona de descarga)

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

##### Evento Satrack GPS (rastreo satelital)

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

##### Evento Last Tracking (reporte manual)

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

### 7. Campos de Monitor NO utilizados por LoggiApp

El servicio `event` de Monitor no está documentado como un servicio independiente en el contrato oficial DD-EST-02. Es un servicio personalizado/extendido que LoggiApp consume. Sin embargo, comparando con la estructura del DTO:

- **No se envía información de la remesa/orden específica** dentro del evento (solo se asocia al manifiesto general).
- **No se utiliza un campo de "idCargo"** dentro del evento para identificar una remesa particular.

> **Nota:** El contrato oficial de Monitor no documenta un servicio `event` con esta estructura. Esto indica que es una funcionalidad adicional o un servicio extendido acordado directamente entre LoggiApp y Monitor fuera del contrato estándar DD-EST-02.

### 8. Transformaciones

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

### 9. Request construido

#### Ejemplo: Evento Loadzone (llegada al cargue)

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

#### Ejemplo: Evento Downloadzone (llegada al descargue)

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

#### Ejemplo: Evento Satrack GPS (rastreo)

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

#### Ejemplo: Evento Last Tracking (reporte manual)

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

### 10. Respuesta esperada

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

### 11. Observaciones

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

---

## Servicio: image

> **Estado: NO ACTIVO** — Infraestructura implementada pero sin uso en producción.

### 1. Nombre

`image`

### 2. Objetivo

Este servicio permite **subir imágenes (evidencia fotográfica) a la plataforma Monitor** asociadas a un despacho. Según el contrato oficial de Monitor, sirve para cargar evidencias como fotos del cargue, descargue, documentos, o cualquier registro visual vinculado a un manifiesto.

### 3. Cuándo se ejecuta

**ESTE SERVICIO NO SE EJECUTA ACTUALMENTE.**

A pesar de que la infraestructura técnica está implementada (DTOs, interfaz del servicio y método en `MonitorServiceImpl`), **no existe ningún lugar en el código fuente de LoggiApp que invoque este servicio.**

No hay:
- Ningún caller de `monitorService.image(...)` en la capa de negocio.
- Ningún método en `MonitorCargoBusinessImpl` que construya un `ImageRequest`.
- Ningún endpoint REST que exponga esta funcionalidad.

### 4. Flujo

No aplica. El servicio no tiene flujo de ejecución activo.

### 5. Lugares donde se llama

**Ninguno.** El servicio está definido pero no invocado.

### 6. Datos enviados a Monitor

Según los DTOs implementados (pero no utilizados), la estructura preparada es:

| Campo Monitor   | Tipo     | Descripción                             | DTO               |
| --------------- | -------- | --------------------------------------- | ----------------- |
| `idManifest`    | String   | Número del manifiesto                   | `Image.idManifest`|
| `path`          | String   | URL/link de visualización de la imagen  | `Image.path`      |
| `dateImage`     | String   | Fecha del archivo                       | `Image.dateImage` |
| `latitude`      | String   | Latitud donde se generó la imagen       | `Image.latitude`  |
| `longitude`     | String   | Longitud donde se generó la imagen      | `Image.longitude` |
| `location`      | String   | Descripción de la ubicación             | `Image.location`  |

### 7. Campos de Monitor NO utilizados por LoggiApp

Según el contrato oficial, el servicio `image` acepta también el campo `album` (nombre del álbum donde se almacenará la imagen). Este campo **no existe en el DTO** `Image` de LoggiApp.

### 8. Transformaciones

No aplica. No hay lógica de construcción del request implementada.

### 9. Request construido

No se genera ningún request actualmente. Basado en el DTO y la estructura SOAP, el request **teórico** sería:

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://service.soap.soapexposer.mayasoft.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:image>
      <authToken>
        <authUser>USUARIO_MONITOR</authUser>
        <authPassword>PASSWORD_MONITOR</authPassword>
      </authToken>
      <image>
        <idManifest>MAN-2025-001234</idManifest>
        <path>https://storage.loggiapp.com/evidencias/foto-cargue-001.jpg</path>
        <dateImage>2025-07-28 09:20:00</dateImage>
        <latitude>4.710989</latitude>
        <longitude>-74.072092</longitude>
        <location>Bodega 5, Calle 80, Bogotá</location>
      </image>
    </ser:image>
  </soapenv:Body>
</soapenv:Envelope>
```

### 10. Respuesta esperada

Seguiría la misma estructura estándar de Monitor:

```xml
<return>
  <code>000</code>
  <description>TRANSACCION EXITOSA</description>
</return>
```

No hay lógica implementada para procesar la respuesta de este servicio a nivel de negocio.

### 11. Observaciones

| #  | Observación |
| -- | ----------- |
| 1  | **Servicio NO activo.** La infraestructura está lista (DTOs + método SOAP) pero no se utiliza en ningún flujo de negocio. |
| 2  | **Posible funcionalidad futura.** La existencia de los DTOs y el método sugiere que fue preparado para uso futuro o que se implementó parcialmente y nunca se conectó. |
| 3  | **El campo `album` del contrato oficial no está en el DTO.** Si se activara este servicio, sería necesario agregar el campo `album` al DTO `Image`. |
| 4  | **No impacta el monitoreo actual.** Los clientes no deben contar con esta funcionalidad de carga de imágenes hacia Monitor como parte de la integración activa. |

---

## Servicio: finalizeShipment

### 1. Nombre

`finalizeShipment`

### 2. Objetivo

Este servicio **finaliza un despacho en la plataforma Monitor**, indicando que el viaje ha concluido y el manifiesto puede darse por terminado. Una vez finalizado, Monitor deja de monitorear activamente el despacho.

### 3. Cuándo se ejecuta

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

### 4. Flujo

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

### 5. Lugares donde se llama

| Clase                     | Método                                                      | Motivo                                                                      | Condición                                             |
| ------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------- |
| `CargoBusinessImpl`       | `reportToMonitorCargo(action, cargo, holderId, ...)`        | Finalizar automáticamente el despacho cuando el conductor completa la entrega| `action == StateCargo.END_SERVICE`                    |
| `CargoServiceImpl` (REST) | `finalizeMonitorShipment(cargoId)`                          | Endpoint REST para finalizar manualmente                                    | `POST /monitor/{cargoId}/finalize`                    |

### 6. Datos enviados a Monitor

| Campo LoggiApp                | Campo Monitor    | Descripción                                    | Obligatorio | Fuente                                                              |
| ----------------------------- | ---------------- | ---------------------------------------------- | :---------: | ------------------------------------------------------------------- |
| `cargo.manifest`              | `idManifest`     | Número del manifiesto a finalizar              | Sí          | `Cargo.manifest`                                                    |
| `cargo.durationTime.endDate`  | `finalizeDate`   | Fecha y hora de finalización del viaje         | Sí          | `Cargo.durationTime.endDate` → hora colombiana `yyyy-MM-dd HH:mm:ss`|

### 7. Campos de Monitor NO utilizados por LoggiApp

El contrato oficial de Monitor define exactamente los mismos campos que LoggiApp envía (`idManifest` y `finalizeDate`). **No hay campos sin utilizar para este servicio.**

### 8. Transformaciones

| Transformación                | Descripción                                                                                                                   |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Fecha a hora colombiana**   | `cargo.durationTime.endDate` (tipo `Date`) se convierte a String en zona horaria de Colombia con formato `yyyy-MM-dd HH:mm:ss` usando `DateUtil.getColombianStringDate()`. |

### 9. Request construido

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

### 10. Respuesta esperada

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

### 11. Observaciones

| #  | Observación |
| -- | ----------- |
| 1  | **Request muy simple.** Solo envía dos campos: el manifiesto y la fecha de finalización. Es el servicio más sencillo de la integración. |
| 2  | **Idempotencia.** Si `monitorState.finalizeShipmentResponse.transmited == true`, la operación se aborta sin reenviar. |
| 3  | **Reintento automático.** Si Monitor responde con error interno (código `001`), se reintenta una vez más. |
| 4  | **Requiere fecha de fin de viaje.** La validación verifica que `cargo.durationTime.endDate` no sea null. Si no existe, se almacena error de validación sin intentar la conexión. |
| 5  | **Ejecución asíncrona.** Se ejecuta en el thread pool `monitorCargoExecutor`. No bloquea la respuesta al usuario. |
| 6  | **Complemento del flujo completo.** Este servicio cierra el ciclo de vida del despacho en Monitor: `loadShipment` (crea) → `event` (monitorea) → `finalizeShipment` (cierra). |

---

## Servicio: cancelShipment

### 1. Nombre

`cancelShipment`

### 2. Objetivo

Este servicio **cancela un despacho en la plataforma Monitor**, indicando que el manifiesto ya no es válido y debe ser anulado. Una vez cancelado, Monitor deja de monitorear el despacho y lo marca como cancelado en su sistema.

### 3. Cuándo se ejecuta

| Aspecto           | Detalle |
| ----------------- | ------- |
| **Evento**        | Una carga es **eliminada** (marcada como `DELETED`) en LoggiApp |
| **Actor**         | Usuario (controlador, despachador, administrador) que elimina la carga desde la interfaz web |
| **Condición 1**   | El `holderId` debe ser `Companies.TECLOGI` |
| **Condición 2**   | El `idCompany` de la carga debe estar en `MonitorCargoCompanies` (Maersk Logistics) |
| **Condición 3**   | La carga NO debe haber sido cancelada previamente en Monitor (`monitorState.cancelShipmentResponse.transmited == false`) |
| **Condición 4**   | La carga debe tener un número de manifiesto (`cargo.manifest` no vacío) |

> **Endpoint REST manual:** `POST /monitor/{cargoId}/cancel`

### 4. Flujo

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

### 5. Lugares donde se llama

| Clase                     | Método                                              | Motivo                                                                    | Condición                                    |
| ------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------- |
| `CargoBusinessImpl`       | `markCargoAsDeleted(cargo, deletedFingerPrint, holderId)` | Cancelar automáticamente el despacho cuando una carga es eliminada  | La carga se marca como `DELETED`             |
| `CargoServiceImpl` (REST) | `cancelMonitorShipment(cargoId)`                    | Endpoint REST para cancelar manualmente                                   | `POST /monitor/{cargoId}/cancel`             |

### 6. Datos enviados a Monitor

| Campo LoggiApp    | Campo Monitor   | Descripción                          | Obligatorio | Fuente           |
| ----------------- | --------------- | ------------------------------------ | :---------: | ---------------- |
| `cargo.manifest`  | `idManifest`    | Número del manifiesto a cancelar     | Sí          | `Cargo.manifest` |

### 7. Campos de Monitor NO utilizados por LoggiApp

El contrato oficial de `cancelShipment` solo requiere `idManifest`. **No hay campos sin utilizar.**

> **Nota:** El contrato también documenta un servicio `cancelCargo` (para cancelar/eliminar una orden de carga individual) con campos `idManifest`, `idCargo` y `delete`. LoggiApp **no implementa `cancelCargo`** — solo cancela el despacho completo.

### 8. Transformaciones

No aplica. El único dato enviado es `cargo.manifest` directamente, sin ninguna transformación.

### 9. Request construido

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

### 10. Respuesta esperada

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

### 11. Observaciones

| #  | Observación |
| -- | ----------- |
| 1  | **Se ejecuta al eliminar la carga, NO al anularla.** La cancelación en Monitor se dispara cuando la carga se marca como `DELETED`, no cuando cambia a un estado de anulación intermedio. |
| 2  | **Request mínimo.** Solo envía el número de manifiesto. Es el servicio con menos datos de toda la integración. |
| 3  | **Idempotencia.** Si `monitorState.cancelShipmentResponse.transmited == true`, la operación se aborta sin reenviar. |
| 4  | **No cancela órdenes individuales.** LoggiApp NO implementa el servicio `cancelCargo` del contrato oficial. Solo cancela el despacho completo (`cancelShipment`). |
| 5  | **No requiere fecha de cancelación.** A diferencia de `finalizeShipment`, la cancelación no incluye fecha. Monitor registra la fecha de cancelación internamente. |
| 6  | **Ejecución asíncrona.** Se ejecuta en el thread pool `monitorCargoExecutor`. La eliminación de la carga no espera la respuesta de Monitor. |
| 7  | **Reintento automático.** Si Monitor responde con error interno (código `001`), se reintenta una vez más. |
