Coloque aqui os artefatos do modelo ICRA esperados pela API:

- `icra_model_v1.joblib`
- `icra_thresholds_v1.json`
- `icra_features_v1.json`

A API carrega esses arquivos no startup. Sem eles, o container `ai` falha no healthcheck.
