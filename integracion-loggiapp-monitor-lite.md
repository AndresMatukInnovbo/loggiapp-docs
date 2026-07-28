# Integración LoggiApp — Monitor

> **Versión:** 1.0 (resumen ejecutivo)  
> **Última actualización:** Julio 2026

---

## ¿Qué es Monitor?

**Monitor** es una plataforma de monitoreo satelital que permite hacer seguimiento en tiempo real a los despachos de carga en carretera. Proporciona visibilidad sobre la ubicación del vehículo, alertas de velocidad, llegadas a puntos de cargue/descargue, y el estado general del viaje.

---

## ¿LoggiApp tiene integración con Monitor?

**Sí.** LoggiApp se conecta automáticamente con Monitor para enviar información de los despachos durante todo su ciclo de vida: desde que el conductor inicia el viaje, hasta que se completa la entrega o se cancela la carga.

La comunicación es **unidireccional en su mayoría**: LoggiApp envía información a Monitor. Monitor la recibe, la procesa y responde con una confirmación.

---

## ¿Qué hace esta integración?

LoggiApp envía a Monitor los siguientes datos de forma automática:

| Acción | Cuándo ocurre | Qué información envía |
| ------ | ------------- | --------------------- |
| **Crear despacho** | Cuando el conductor inicia el viaje | Manifiesto, ruta, vehículo (placa), conductor, órdenes de carga (remesas) con origen, destino, remitente, destinatario y mercancía |
| **Reportar llegada al cargue** | Inmediatamente después de crear el despacho | Fecha, coordenadas y dirección del sitio de cargue |
| **Reportar llegada al descargue** | Cuando el conductor confirma la llegada a un destino | Fecha, coordenadas y dirección del sitio de descargue |
| **Enviar ubicación GPS** | Cuando el proveedor GPS (Satrack) detecta un cambio de estado del vehículo | Coordenadas, velocidad, estado del motor (encendido/apagado/detenido), temperatura |
| **Enviar alertas** | Cuando se detecta exceso de velocidad, desconexión de antena GPS o desviación de ruta | Tipo de alerta, ubicación y velocidad |
| **Reportar novedades** | Cuando un conductor o controlador registra manualmente un punto de trazabilidad | Descripción, coordenadas y dirección |
| **Finalizar despacho** | Cuando el conductor completa la entrega (fin del servicio) | Número de manifiesto y fecha de finalización |
| **Cancelar despacho** | Cuando un usuario elimina la carga en LoggiApp | Número de manifiesto |

---

## ¿En qué momento del viaje se activa cada servicio?

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CICLO DE VIDA DEL DESPACHO                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. INICIO DEL VIAJE                                                 │
│     └─► Crear despacho en Monitor (loadShipment)                     │
│     └─► Reportar llegada al cargue (event: loadzone)                 │
│                                                                      │
│  2. DURANTE EL VIAJE                                                 │
│     └─► Enviar ubicación GPS automáticamente (event: lastgps)        │
│     └─► Enviar alertas: exceso velocidad, GPS, desviación           │
│     └─► Reportar novedades manuales (event: lasttracking)           │
│                                                                      │
│  3. LLEGADA A DESTINO                                                │
│     └─► Reportar llegada al descargue (event: downloadzone)          │
│                                                                      │
│  4. FIN DEL VIAJE                                                    │
│     └─► Finalizar despacho en Monitor (finalizeShipment)             │
│                                                                      │
│  ✕ CANCELACIÓN (si aplica)                                           │
│     └─► Cancelar despacho en Monitor (cancelShipment)                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Información que LoggiApp envía a Monitor

### Al crear el despacho

| Categoría | Datos enviados |
| --------- | -------------- |
| **Manifiesto** | Número de manifiesto, fecha de expedición, fecha de salida, tipo de operación (Nacional/Urbano), observaciones |
| **Generador** | NIT y nombre de la empresa dueña de la carga |
| **Transportador** | NIT y nombre de la empresa transportadora |
| **Ruta** | Nombre del itinerario, código DANE municipio origen, código DANE municipio destino |
| **Vehículo** | Placa |
| **Conductor** | Cédula, nombre, apellido, celular |
| **Por cada remesa** | ID de la orden, número de remesa, cita de carga, cita de descarga, contenedor (si aplica), categoría de la mercancía, nombre del producto, datos del remitente (NIT, nombre, municipio, dirección), datos del destinatario (NIT, nombre, municipio, dirección) |

### En los eventos de rastreo

| Dato | Descripción |
| ---- | ----------- |
| Número de manifiesto | Identifica a qué despacho pertenece el evento |
| Tipo de evento | Llegada al cargue, llegada al descargue, posición GPS, alerta, novedad |
| Fecha y hora | Momento exacto del evento |
| Coordenadas | Latitud y longitud |
| Dirección | Descripción textual de la ubicación |
| Velocidad | Km/h del vehículo (solo en eventos GPS) |
| Estado del motor | Encendido / Apagado / Detenido (solo en eventos GPS) |
| Temperatura | Si el vehículo tiene sensor de temperatura |

---

## Alertas que se reportan a Monitor

| Alerta | Cuándo se genera |
| ------ | ---------------- |
| **Exceso de velocidad** | Cuando el GPS reporta velocidad superior a 75 km/h, o cuando Satrack genera un evento de código 24 |
| **GPS desconectado** | Cuando Satrack detecta que la antena GPS fue desconectada (evento código 27) |
| **Desviación de ruta** | Cuando Satrack detecta un giro repentino o cambio brusco de dirección (evento código 600) |

---

## Comportamiento automático

La integración funciona de forma **completamente automática**. No requiere intervención del usuario para:

- Crear el despacho en Monitor (se dispara al iniciar viaje).
- Enviar eventos de ubicación (se dispara por el sistema GPS).
- Finalizar el despacho (se dispara al completar la entrega).
- Cancelar el despacho (se dispara al eliminar la carga).

Adicionalmente, existe la posibilidad de **re-ejecutar manualmente** cualquier operación desde la interfaz web en caso de fallas o reintentos.

---

## Restricción de activación

Actualmente existe una condicional en el sistema que permite activar la integración con Monitor **solo para una empresa específica configurada**. El resto de empresas no dispara el envío automático a Monitor, aunque la funcionalidad exista en la plataforma.

> La habilitación para nuevas empresas es un cambio de configuración, no un cambio de contrato con Monitor.

---

## ¿Qué pasa si Monitor falla?

| Situación | Comportamiento de LoggiApp |
| --------- | -------------------------- |
| Monitor responde exitosamente | Se marca como transmitido. No se reenvía. |
| Monitor responde con error interno | Se **reintenta una vez** automáticamente. Si falla de nuevo, se guarda como no transmitido. |
| Monitor no responde o hay error de red | Se guarda como no transmitido. Se puede reintentar manualmente. |
| El despacho ya existe en Monitor | Se considera exitoso. No genera error. |

La integración **nunca bloquea** el flujo operativo de LoggiApp. Si Monitor está caído, el conductor puede seguir trabajando normalmente.

---

## ¿Qué del contrato de Monitor aún NO está implementado?

Las siguientes funcionalidades están disponibles en Monitor pero LoggiApp **aún no las usa**:

| Funcionalidad | Qué permitiría hacer | Estado |
| ------------- | -------------------- | ------ |
| Actualizar despacho | Modificar datos del viaje después de creado (ej: cambio de conductor o ruta) | No implementado |
| Agregar/modificar remesas | Añadir nuevas órdenes de carga a un despacho ya existente | No implementado |
| Cancelar remesa individual | Anular una remesa específica sin afectar el resto del despacho | No implementado |
| Tiempos logísticos detallados | Enviar inicio/fin de cargue y descargue por separado | No implementado |
| Radicado RNDC | Informar a Monitor el número de radicado del manifiesto | No implementado |
| Subir imágenes | Enviar evidencias fotográficas del viaje | Infraestructura lista, pendiente de activación |

---

## Resumen de cobertura

| Lo que Monitor ofrece | ¿LoggiApp lo usa? |
| --------------------- | :---------------: |
| Crear despacho | Si |
| Eventos de rastreo GPS | Si |
| Alertas (velocidad, GPS, desviación) | Si |
| Eventos de llegada (cargue/descargue) | Si |
| Novedades manuales | Si |
| Finalizar despacho | Si |
| Cancelar despacho | Si |
| Actualizar despacho ya creado | No |
| Gestionar remesas individuales | No |
| Tiempos logísticos detallados | No |
| Radicado RNDC | No |
| Subir imágenes/evidencia | Pendiente |
