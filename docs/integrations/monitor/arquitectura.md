# Arquitectura

## Protocolo de comunicación

| Aspecto          | Detalle                                                         |
| ---------------- | --------------------------------------------------------------- |
| Protocolo        | SOAP sobre HTTP/HTTPS                                           |
| Método HTTP      | POST                                                            |
| Content-Type     | `text/xml; charset=utf-8`                                       |
| Namespace SOAP   | Definido por el contrato oficial de Monitor                     |
| URL del servicio | Configurada por ambiente (desarrollo / producción)              |

---

## Componentes principales

```
┌─────────────────────┐         SOAP/HTTP          ┌──────────────────┐
│     LoggiApp        │ ─────────────────────────►  │     Monitor      │
│                     │                             │                  │
│  Capa de negocio    │  LoadShipmentRequest        │  Recibe y        │
│       ↓             │  EventRequest               │  monitorea       │
│  Cliente SOAP       │  FinalizeShipmentRequest    │  despachos       │
│       ↓             │  CancelShipmentRequest      │                  │
│  Conexión HTTP      │  ImageRequest               │                  │
│                     │ ◄───────────────────────── │  MonitorResponse │
└─────────────────────┘                             └──────────────────┘
```

---

## Ejecución asíncrona

Todas las operaciones de integración con Monitor se ejecutan de forma **asíncrona** usando un thread pool dedicado. Esto garantiza que una falla en Monitor no bloquee el flujo principal de la aplicación.

---

## Restricción de activación

Actualmente existe una **condicional en el código** que limita la activación de la integración: solo una empresa específica configurada en el sistema puede superar esta validación y enviar información a Monitor. El resto de empresas no dispara la integración, aunque el código de los servicios exista.

> La habilitación para nuevas empresas es un cambio de configuración/código, no un cambio de contrato con Monitor.

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
