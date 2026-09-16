import React from 'react';
import { ViewStyle } from 'react-native';
import WebView from 'react-native-webview';

export interface SkeletonFrame {
  joints: [number, number, number][];
}

interface ThreeJSViewerProps {
  skeletonData: SkeletonFrame[];
  style?: ViewStyle;
}

const COCO17_EDGES: [number, number][] = [
  [0, 5], [0, 6], [5, 6], [5, 7], [7, 9],
  [6, 8], [8, 10], [5, 11], [6, 12], [11, 12],
  [11, 13], [13, 15], [12, 14], [14, 16],
];

const HTML = `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0a0a0a; overflow: hidden; width: 100vw; height: 100vh; }
  canvas { display: block; width: 100vw; height: 100vh; }
  #scrubber {
    position: absolute;
    bottom: 12px;
    left: 12px;
    right: 12px;
    height: 4px;
    accent-color: #00c853;
    cursor: pointer;
  }
</style>
</head>
<body>
<canvas id="c"></canvas>
<input id="scrubber" type="range" min="0" step="1" value="0">
<script src="https://cdn.jsdelivr.net/npm/three@0.168.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.168.0/examples/js/controls/OrbitControls.js"></script>
<script>
(function () {
  var data = window.SKELETON_DATA || [];
  var edges = ${JSON.stringify(COCO17_EDGES)};
  var numFrames = data.length;

  var canvas = document.getElementById('c');
  var scrubber = document.getElementById('scrubber');
  scrubber.max = Math.max(0, numFrames - 1);

  var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x0a0a0a, 1);

  var scene = new THREE.Scene();

  var camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.01, 100);
  camera.position.set(0, 0, 3);

  var ambient = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambient);
  var dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(1, 2, 3);
  scene.add(dirLight);

  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.1;
  controls.enablePan = false;
  controls.minDistance = 0.5;
  controls.maxDistance = 10;

  var jointMeshes = [];
  var lineMeshes = [];
  var jointGeo = null;
  var jointMat = new THREE.MeshStandardMaterial({ color: 0x00c853 });
  var lineMat = new THREE.LineBasicMaterial({ color: 0x00c853 });

  function computeExtent(frame) {
    if (!frame || !frame.joints || frame.joints.length === 0) return 1;
    var minX = Infinity, maxX = -Infinity;
    var minY = Infinity, maxY = -Infinity;
    var minZ = Infinity, maxZ = -Infinity;
    frame.joints.forEach(function (j) {
      if (j[0] < minX) minX = j[0]; if (j[0] > maxX) maxX = j[0];
      if (j[1] < minY) minY = j[1]; if (j[1] > maxY) maxY = j[1];
      if (j[2] < minZ) minZ = j[2]; if (j[2] > maxZ) maxZ = j[2];
    });
    return Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 1;
  }

  function computeCenter(frame) {
    if (!frame || !frame.joints || frame.joints.length === 0) return [0, 0, 0];
    var sx = 0, sy = 0, sz = 0, n = frame.joints.length;
    frame.joints.forEach(function (j) { sx += j[0]; sy += j[1]; sz += j[2]; });
    return [sx / n, sy / n, sz / n];
  }

  var scale = 1;
  var cx = 0, cy = 0, cz = 0;

  if (numFrames > 0) {
    var firstFrame = data[0];
    var extent = computeExtent(firstFrame);
    scale = 1.2 / extent;
    var c = computeCenter(firstFrame);
    cx = c[0]; cy = c[1]; cz = c[2];
    var r = 0.025;
    jointGeo = new THREE.SphereGeometry(r, 8, 8);
    for (var i = 0; i < 17; i++) {
      var mesh = new THREE.Mesh(jointGeo, jointMat);
      scene.add(mesh);
      jointMeshes.push(mesh);
    }
    for (var e = 0; e < edges.length; e++) {
      var points = [new THREE.Vector3(), new THREE.Vector3()];
      var geo = new THREE.BufferGeometry().setFromPoints(points);
      var line = new THREE.Line(geo, lineMat);
      scene.add(line);
      lineMeshes.push(line);
    }
  }

  function applyFrame(frameIdx) {
    if (numFrames === 0) return;
    var frame = data[frameIdx];
    if (!frame || !frame.joints) return;
    for (var i = 0; i < jointMeshes.length && i < frame.joints.length; i++) {
      var j = frame.joints[i];
      jointMeshes[i].position.set(
        (j[0] - cx) * scale,
        (j[1] - cy) * scale,
        (j[2] - cz) * scale
      );
    }
    for (var e = 0; e < edges.length && e < lineMeshes.length; e++) {
      var a = edges[e][0], b = edges[e][1];
      if (a >= frame.joints.length || b >= frame.joints.length) continue;
      var ja = frame.joints[a], jb = frame.joints[b];
      var positions = new Float32Array([
        (ja[0] - cx) * scale, (ja[1] - cy) * scale, (ja[2] - cz) * scale,
        (jb[0] - cx) * scale, (jb[1] - cy) * scale, (jb[2] - cz) * scale,
      ]);
      lineMeshes[e].geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      lineMeshes[e].geometry.attributes.position.needsUpdate = true;
    }
  }

  applyFrame(0);

  scrubber.addEventListener('input', function () {
    applyFrame(parseInt(scrubber.value, 10));
    stopAutoplay = true;
  });

  var currentFrame = 0;
  var stopAutoplay = false;
  var lastTime = null;
  var mspf = 1000 / 30;

  function animate(ts) {
    requestAnimationFrame(animate);
    if (!stopAutoplay && numFrames > 1) {
      if (lastTime === null) lastTime = ts;
      if (ts - lastTime >= mspf) {
        lastTime = ts;
        currentFrame = (currentFrame + 1) % numFrames;
        scrubber.value = currentFrame;
        applyFrame(currentFrame);
      }
    }
    controls.update();
    renderer.render(scene, camera);
  }

  requestAnimationFrame(animate);

  window.addEventListener('resize', function () {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
})();
</script>
</body>
</html>`;

export default function ThreeJSViewer({ skeletonData, style }: ThreeJSViewerProps) {
  const injected = `window.SKELETON_DATA = ${JSON.stringify(skeletonData)};`;

  return (
    <WebView
      style={style}
      source={{ html: HTML }}
      originWhitelist={['*']}
      javaScriptEnabled
      scrollEnabled={false}
      injectedJavaScriptBeforeContentLoaded={injected}
    />
  );
}
