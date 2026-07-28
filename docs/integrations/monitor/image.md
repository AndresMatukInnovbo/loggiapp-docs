# Servicio: image

!!! warning "Estado: NO ACTIVO"

    Infraestructura implementada pero sin uso en producción.

## 1. Nombre

`image`

## 2. Objetivo

Este servicio permite **subir imágenes (evidencia fotográfica) a la plataforma Monitor** asociadas a un despacho. Según el contrato oficial de Monitor, sirve para cargar evidencias como fotos del cargue, descargue, documentos, o cualquier registro visual vinculado a un manifiesto.

## 3. Cuándo se ejecuta

**ESTE SERVICIO NO SE EJECUTA ACTUALMENTE.**

A pesar de que la infraestructura técnica está implementada (DTOs, interfaz del servicio y método en `MonitorServiceImpl`), **no existe ningún lugar en el código fuente de LoggiApp que invoque este servicio.**

No hay:

- Ningún caller de `monitorService.image(...)` en la capa de negocio.
- Ningún método en `MonitorCargoBusinessImpl` que construya un `ImageRequest`.
- Ningún endpoint REST que exponga esta funcionalidad.

## 4. Flujo

No aplica. El servicio no tiene flujo de ejecución activo.

## 5. Lugares donde se llama

**Ninguno.** El servicio está definido pero no invocado.

## 6. Datos enviados a Monitor

Según los DTOs implementados (pero no utilizados), la estructura preparada es:

| Campo Monitor   | Tipo     | Descripción                             | DTO               |
| --------------- | -------- | --------------------------------------- | ----------------- |
| `idManifest`    | String   | Número del manifiesto                   | `Image.idManifest`|
| `path`          | String   | URL/link de visualización de la imagen  | `Image.path`      |
| `dateImage`     | String   | Fecha del archivo                       | `Image.dateImage` |
| `latitude`      | String   | Latitud donde se generó la imagen       | `Image.latitude`  |
| `longitude`     | String   | Longitud donde se generó la imagen      | `Image.longitude` |
| `location`      | String   | Descripción de la ubicación             | `Image.location`  |

## 7. Campos de Monitor NO utilizados por LoggiApp

Según el contrato oficial, el servicio `image` acepta también el campo `album` (nombre del álbum donde se almacenará la imagen). Este campo **no existe en el DTO** `Image` de LoggiApp.

## 8. Transformaciones

No aplica. No hay lógica de construcción del request implementada.

## 9. Request construido

No se genera ningún request actualmente. Basado en el DTO y la estructura SOAP, el request **teórico** sería:

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="[NAMESPACE_SOAP_MONITOR]">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:image>
      <!-- authToken omitido: la autenticación se gestiona internamente por la plataforma -->
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

## 10. Respuesta esperada

Seguiría la misma estructura estándar de Monitor:

```xml
<return>
  <code>000</code>
  <description>TRANSACCION EXITOSA</description>
</return>
```

No hay lógica implementada para procesar la respuesta de este servicio a nivel de negocio.

## 11. Observaciones

| #  | Observación |
| -- | ----------- |
| 1  | **Servicio NO activo.** La infraestructura está lista (DTOs + método SOAP) pero no se utiliza en ningún flujo de negocio. |
| 2  | **Posible funcionalidad futura.** La existencia de los DTOs y el método sugiere que fue preparado para uso futuro o que se implementó parcialmente y nunca se conectó. |
| 3  | **El campo `album` del contrato oficial no está en el DTO.** Si se activara este servicio, sería necesario agregar el campo `album` al DTO `Image`. |
| 4  | **No impacta el monitoreo actual.** Los clientes no deben contar con esta funcionalidad de carga de imágenes hacia Monitor como parte de la integración activa. |
