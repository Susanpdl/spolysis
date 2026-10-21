import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const edges = [
  [17, 0],
  [5, 6],
  [5, 7],
  [7, 9],
  [6, 8],
  [8, 10],
  [5, 11],
  [6, 12],
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
];
const scene = new THREE.Scene();
scene.background = new THREE.Color("#101914");
const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100);
camera.position.set(0, 1.2, 4.5);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
document.getElementById("canvas").appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.3, 0);
controls.enablePan = false;
controls.minDistance = 1.5;
controls.maxDistance = 8;
const grid = new THREE.GridHelper(6, 12, "#365344", "#253b2f");
grid.position.y = -1;
scene.add(grid);
scene.add(new THREE.HemisphereLight(0xffffff, 0x233f2f, 3));
function skeleton(color, opacity) {
  const group = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({
    color,
    transparent: opacity < 1,
    opacity,
  });
  const joints = Array.from({ length: 18 }, (_, i) => {
    const joint = new THREE.Mesh(new THREE.SphereGeometry(i === 0 ? 0.06 : 0.026, 10, 10), mat);
    joint.visible = i === 0 || (i >= 5 && i < 17);
    group.add(joint);
    return joint;
  });
  const bones = edges.map(() => {
    const bone = new THREE.Mesh(
      new THREE.CylinderGeometry(0.014, 0.014, 1, 8),
      mat,
    );
    group.add(bone);
    return bone;
  });
  scene.add(group);
  return { group, joints, bones };
}
const corrected = skeleton("#53ed9c", 1);
const original = skeleton("#80baff", 0.45);
let data,
  frame = 0,
  playing = false,
  lastTime = 0,
  accumulator = 0,
  scale = 1;
const scrub = document.getElementById("scrub");
const play = document.getElementById("play");
function showPose(model, pose) {
  model.joints.forEach((joint, i) => {
    // The shoulder midpoint is a display-only neck anchor, not an extra estimate.
    if (i === 17) {
      joint.position.copy(model.joints[5].position).add(model.joints[6].position).multiplyScalar(0.5);
    } else {
      joint.position.fromArray(pose[i]).multiplyScalar(scale);
    }
  });
  model.bones.forEach((bone, i) => {
    const a = model.joints[edges[i][0]].position;
    const b = model.joints[edges[i][1]].position;
    const vector = b.clone().sub(a);
    bone.position.copy(a).add(b).multiplyScalar(0.5);
    bone.scale.set(1, vector.length(), 1);
    bone.quaternion.setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      vector.normalize(),
    );
  });
}
function drawFrame() {
  if (!data) return;
  showPose(corrected, data.frames[frame]);
  if (data.original_frames) showPose(original, data.original_frames[frame]);
  original.group.visible =
    !!data.original_frames && document.getElementById("compare").checked;
  scrub.value = frame;
  document.getElementById("time").textContent =
    `${(frame / data.fps).toFixed(1)} / ${((data.frames.length - 1) / data.fps).toFixed(1)} s`;
}
window.setSkeleton = (payload) => {
  try {
    if (!payload.frames?.length) throw new Error("No motion frames available.");
    data = payload;
    data.fps = data.fps || 30;
    const ys = data.frames[0].slice(5).map((p) => p[1]);
    scale = 1.8 / Math.max(Math.max(...ys) - Math.min(...ys), 0.01);
    grid.position.y = Math.min(...ys) * scale - 0.03;
    frame = 0;
    scrub.max = data.frames.length - 1;
    drawFrame();
  } catch (error) {
    window.ReactNativeWebView?.postMessage(
      JSON.stringify({ error: error.message }),
    );
  }
};
play.onclick = () => {
  playing = !playing;
  play.textContent = playing ? "Pause" : "Play";
};
scrub.oninput = () => {
  frame = Number(scrub.value);
  drawFrame();
};
document.getElementById("compare").onchange = drawFrame;
document.getElementById("reset").onclick = () => {
  camera.position.set(0, 1.2, 4.5);
  controls.target.set(0, 0.3, 0);
  controls.update();
};
function resize() {
  const element = document.getElementById("canvas");
  renderer.setSize(element.clientWidth, element.clientHeight);
  camera.aspect = element.clientWidth / element.clientHeight;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();
renderer.setAnimationLoop((time) => {
  if (data && playing) {
    accumulator += Math.min(time - lastTime, 100);
    const step = 1000 / data.fps;
    if (accumulator >= step) {
      frame = (frame + Math.floor(accumulator / step)) % data.frames.length;
      accumulator %= step;
      drawFrame();
    }
  }
  lastTime = time;
  controls.update();
  renderer.render(scene, camera);
});
window.ReactNativeWebView?.postMessage(JSON.stringify({ ready: true }));
