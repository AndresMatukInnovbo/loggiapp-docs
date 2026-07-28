# FAQ — Preguntas frecuentes

## ¿Para qué empresas está habilitada la integración?

Actualmente existe una condicional en el código que permite activar la integración solo para una empresa específica configurada en el sistema. El resto de empresas no dispara el envío a Monitor.

> La habilitación para nuevas empresas es un cambio de configuración/código, no un cambio de contrato con Monitor.

---

## ¿Qué pasa si Monitor no responde o falla?

Todas las operaciones se ejecutan de forma **asíncrona** usando un thread pool dedicado. Una falla en Monitor **no bloquea** el flujo principal de la aplicación.

Si Monitor responde con error interno (código `001`), se **reintenta una vez** más automáticamente. Si falla de nuevo, se guarda como no transmitido.

---

## ¿Se puede re-ejecutar un servicio manualmente?

Sí. Existen endpoints REST para ejecutar manualmente cada servicio:

| Servicio          | Endpoint                                                  |
| ----------------- | --------------------------------------------------------- |
| loadShipment      | `POST /monitor/{cargoId}/load-shipment`                   |
| loadzone event    | `POST /monitor/{cargoId}/loadzone-event`                  |
| downloadzone event| `POST /monitor/{cargoId}/downloadzone-event`              |
| last tracking     | `POST /monitor/{cargoId}/last-tracking-event`             |
| finalizeShipment  | `POST /monitor/{cargoId}/finalize`                        |
| cancelShipment    | `POST /monitor/{cargoId}/cancel`                          |

---

## ¿Qué significa cada código de respuesta de Monitor?

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

## ¿Por qué el servicio `event` no aparece en el contrato oficial?

El contrato oficial de Monitor (DD-EST-02) **no documenta** un servicio `event` con la estructura que LoggiApp utiliza. Esto indica que es una funcionalidad adicional o un servicio extendido acordado directamente entre LoggiApp y Monitor fuera del contrato estándar.

---

## ¿Qué servicios del contrato oficial faltan por implementar?

| Servicio                    | Estado       |
| --------------------------- | ------------ |
| `updateShipment`            | No implementado |
| `upsertCargo`               | No implementado |
| `cancelCargo`               | No implementado |
| `logisticTime`              | No implementado |
| `updateSubmittedmanifest`   | No implementado |

Para más detalles del impacto, consulta la [página de introducción](index.md#servicios-del-contrato-oficial-no-implementados-en-loggiapp).

---

## ¿El servicio `image` está activo?

No. La infraestructura está lista (DTOs + método SOAP) pero **no se utiliza** en ningún flujo de negocio. No existe ningún caller que invoque este servicio. Para más detalles, consulta la [documentación del servicio image](image.md).

---

## ¿Cómo se maneja la autenticación?

La autenticación hacia Monitor se gestiona internamente por la plataforma. No se documentan credenciales ni tokens en esta guía.

---

## ¿Cuál es el ciclo de vida completo de un despacho en Monitor?

```
loadShipment (crea el despacho)
        ↓
event - loadzone (llegada al cargue)
        ↓
event - lastgps/satrack (rastreo durante el viaje)
        ↓
event - downloadzone (llegada al descargue)
        ↓
finalizeShipment (cierra el despacho)
```

Si el despacho se cancela en cualquier punto: `cancelShipment` (anula el despacho).
