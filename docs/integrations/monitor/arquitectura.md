# Arquitectura

## Protocolo de comunicación

| Aspecto          | Detalle                                                         |
| ---------------- | --------------------------------------------------------------- |
| Protocolo        | SOAP sobre HTTP/HTTPS                                           |
| Método HTTP      | POST                                                            |
| Content-Type     | `text/xml; charset=utf-8`                                       |
| Namespace SOAP   | `http://service.soap.soapexposer.mayasoft.com/`                 |
| URL Producción   | Configurada en `monitor.soap.prod` (properties)                 |
| URL Desarrollo   | `https://monitorpiloto.mayasoft.ai/soap/ws/LoadShipment?wsdl`   |

---

## Componentes principales

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

---

## Autenticación

| Ambiente     | Mecanismo                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------- |
| Producción   | Credenciales almacenadas en base de datos (`CompanySAAS.integrationCredentials`) por empresa (holder), canal `MONITOR_CARGO`. |
| Desarrollo   | Credenciales hardcodeadas: usuario `PILOTO`, contraseña `PILOTO`.                                 |

---

## Ejecución asíncrona

Todas las operaciones de integración con Monitor se ejecutan de forma **asíncrona** usando un thread pool dedicado (`monitorCargoExecutor`) mediante la anotación `@Async`. Esto garantiza que una falla en Monitor no bloquee el flujo principal de la aplicación.

---

## Restricción de empresas

La integración **solo se activa** para empresas que cumplan ambas condiciones:

1. El `holderId` sea igual a `Companies.TECLOGI` (la plataforma Teclogi).
2. El `idCompany` de la carga esté registrado en `MonitorCargoCompanies` (actualmente solo **Maersk Logistics** — NIT: `83008063410`).

---

## Respuesta estándar de Monitor

| Código | Descripción              | Significado                             |
| ------ | ------------------------ | --------------------------------------- |
| 000    | TRANSACCION EXITOSA      | Operación procesada correctamente       |
| 001    | ERROR INTERNO            | Error no controlado en Monitor          |
| 002    | PARAMETRO OBLIGATORIO    | Falta un campo requerido                |
| 003    | FORMATO NO VALIDO        | Valor con formato incorrecto            |
| 004    | CREDENCIALES INVALIDAS   | Usuario/contraseña incorrectos          |
| 005    | VALOR FUERA DE RANGO     | Campo excede longitud permitida         |
| 006    | DESPACHO YA EXISTE       | El despacho ya fue creado previamente   |
