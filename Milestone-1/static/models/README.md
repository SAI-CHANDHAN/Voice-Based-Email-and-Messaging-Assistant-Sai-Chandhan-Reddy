Place face-api model files here

To run face-api locally, download the model artifacts and put them under this folder.
Recommended models for this project (from vladmandic/face-api):

- tiny_face_detector_model-weights_manifest.json
- tiny_face_detector_model-shard1
- face_landmark_68_model-weights_manifest.json
- face_landmark_68_model-shard1
- face_recognition_model-weights_manifest.json
- face_recognition_model-shard1

Exact filenames and shard names depend on the build; if you downloaded a zipped `models/` folder, place its contents here so that `faceapi.nets.*.loadFromUri("/static/models/")` finds the expected files.

Where to download:
- Official repo: https://github.com/vladmandic/face-api
- CDN: https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/  (you can mirror these files locally)

After placing real files, remove this README or keep it for reference.
