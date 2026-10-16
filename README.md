# loggiapp-docs

Portal de documentación de LoggiApp (MkDocs + Material). Publicado en https://andresmatukinnovbo.github.io/loggiapp-docs/

## Documentación de funcionalidades (automatizada)

Los documentos de `docs/funcionalidades/` **no se editan aquí**: son un espejo de
`pom-teclogi/docs/features/` en el repo `teclogi-github/TecLogi-Server-Java-`, escritos con la plantilla
técnica 3.1.0 y renderizados por `hooks/docflow.py`.

- **Publicación:** cada push a la rama configurada en TecLogi-Server-Java- que toque
  `pom-teclogi/docs/features/**` ejecuta `.github/workflows/publish-feature-docs.yml` (en ese repo),
  que sincroniza los `.md`, hace `mkdocs gh-deploy --strict` y actualiza la rama `gh-pages`.
- **En local:**
  ```
  python scripts/sync_features.py      # copia desde ..\TecLogi-Server-Java\TecLogi-Server-Java-\pom-teclogi\docs\features
  mkdocs serve                         # http://127.0.0.1:8000/
  ```
  Otro origen: `python scripts/sync_features.py <carpeta>` o la variable `FEATURES_SRC`.
