import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const edges = [
  { a: 17, b: 0, top: 0.043, bottom: 0.05 },
  { a: 5, b: 6, top: 0.075, bottom: 0.075 },
  { a: 5, b: 7, top: 0.07, bottom: 0.058 },
  { a: 7, b: 9, top: 0.056, bottom: 0.04 },
  { a: 6, b: 8, top: 0.07, bottom: 0.058 },
  { a: 8, b: 10, top: 0.056, bottom: 0.04 },
  { a: 5, b: 11, top: 0.065, bottom: 0.056 },
  { a: 6, b: 12, top: 0.065, bottom: 0.056 },
  { a: 11, b: 12, top: 0.085, bottom: 0.085 },
  { a: 11, b: 13, top: 0.078, bottom: 0.058 },
  { a: 13, b: 15, top: 0.058, bottom: 0.043 },
  { a: 12, b: 14, top: 0.078, bottom: 0.058 },
  { a: 14, b: 16, top: 0.058, bottom: 0.043 },
];
const focusJointIndices = {
  right_elbow: 8,
  left_elbow: 7,
  right_knee: 14,
  left_knee: 13,
  right_shoulder_abduction: 6,
  left_shoulder_abduction: 5,
};
const scene = new THREE.Scene();
scene.background = new THREE.Color("#cad9d4");
const camera = new THREE.PerspectiveCamera(24, 1, 0.01, 100);
const playerBaseline = -11.885;
const frontCameraPosition = new THREE.Vector3(9, 1.6, 5);
const frontCameraTarget = new THREE.Vector3(0, 0.55, playerBaseline + 1.8);
camera.position.copy(frontCameraPosition);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;
document.getElementById("canvas").appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(frontCameraTarget);
controls.enablePan = false;
controls.minDistance = 3;
controls.maxDistance = 28;
controls.enableDamping = true;
controls.dampingFactor = 0.08;
const stage = new THREE.Group();
scene.add(stage);
const court = new THREE.Group();
stage.add(court);
const playerStage = new THREE.Group();
playerStage.position.z = playerBaseline;
stage.add(playerStage);

function courtPlane(width, length, color, y) {
  const plane = new THREE.Mesh(
    new THREE.PlaneGeometry(width, length),
    new THREE.MeshStandardMaterial({ color, roughness: 0.94 }),
  );
  plane.rotation.x = -Math.PI / 2;
  plane.position.y = y;
  plane.receiveShadow = true;
  court.add(plane);
  return plane;
}

function courtStrip(width, length, x, z, y, color = "#f2f3ec") {
  const line = new THREE.Mesh(
    new THREE.BoxGeometry(width, 0.012, length),
    new THREE.MeshStandardMaterial({ color, roughness: 0.85 }),
  );
  line.position.set(x, y, z);
  court.add(line);
  return line;
}

courtPlane(60, 60, "#567b69", -0.04);
courtPlane(11.1, 23.9, "#397c70", -0.015);
const courtLineY = 0.002;
const courtHalfWidth = 5.49;
const courtHalfLength = 11.885;
const lineWidth = 0.035;
courtStrip(lineWidth, 23.77, -courtHalfWidth, 0, courtLineY);
courtStrip(lineWidth, 23.77, courtHalfWidth, 0, courtLineY);
courtStrip(10.97, lineWidth, 0, -courtHalfLength, courtLineY);
courtStrip(lineWidth, 23.77, -4.115, 0, courtLineY);
courtStrip(lineWidth, 23.77, 4.115, 0, courtLineY);
courtStrip(8.23, lineWidth, 0, -6.4, courtLineY);
courtStrip(8.23, lineWidth, 0, 6.4, courtLineY);
courtStrip(lineWidth, 12.8, 0, 0, courtLineY);

const net = new THREE.Mesh(
  new THREE.BoxGeometry(10.97, 0.78, 0.035),
  new THREE.MeshStandardMaterial({
    color: "#263e3b",
    roughness: 0.9,
    transparent: true,
    opacity: 0.82,
  }),
);
net.position.set(0, 0.42, 0);
court.add(net);
const netBand = new THREE.Mesh(
  new THREE.BoxGeometry(11.02, 0.075, 0.06),
  new THREE.MeshStandardMaterial({ color: "#f4f4ee", roughness: 0.7 }),
);
netBand.position.set(0, 0.83, 0);
court.add(netBand);
for (const x of [-5.53, 5.53]) {
  const post = new THREE.Mesh(
    new THREE.CylinderGeometry(0.035, 0.035, 0.96, 12),
    new THREE.MeshStandardMaterial({ color: "#e4e4db", roughness: 0.55 }),
  );
  post.position.set(x, 0.46, 0);
  court.add(post);
}

const groundShadow = new THREE.Mesh(
  new THREE.CircleGeometry(0.48, 40),
  new THREE.MeshBasicMaterial({
    color: "#142721",
    transparent: true,
    opacity: 0.26,
    depthWrite: false,
  }),
);
groundShadow.rotation.x = -Math.PI / 2;
groundShadow.scale.y = 1.45;
groundShadow.position.y = 0.012;
playerStage.add(groundShadow);

const racketPathGeometry = new THREE.BufferGeometry();
const racketPath = new THREE.Line(
  racketPathGeometry,
  new THREE.LineBasicMaterial({
    color: "#ffc45c",
    transparent: true,
    opacity: 0.92,
    depthTest: false,
  }),
);
racketPath.renderOrder = 2;
playerStage.add(racketPath);
scene.add(new THREE.HemisphereLight(0xffffff, 0xaaa2c2, 1.45));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
keyLight.position.set(-2.5, 4, 4);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0xe8deff, 0.7);
rimLight.position.set(2, 2.4, -3);
scene.add(rimLight);

const jointRadii = {
  5: 0.075,
  6: 0.075,
  7: 0.057,
  8: 0.057,
  9: 0.043,
  10: 0.043,
  11: 0.088,
  12: 0.088,
  13: 0.068,
  14: 0.068,
  15: 0.052,
  16: 0.052,
  17: 0.048,
};

function skeleton(color, opacity) {
  const group = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({
    color,
    transparent: opacity < 1,
    opacity,
    roughness: 0.52,
    metalness: 0.02,
    depthWrite: opacity >= 1,
    depthTest: opacity >= 1,
    wireframe: opacity < 1,
  });
  const joints = Array.from({ length: 18 }, (_, i) => {
    const radius = jointRadii[i] ?? 0.025;
    const joint = new THREE.Mesh(new THREE.SphereGeometry(radius, 12, 8), mat);
    joint.visible = i === 17 || (i >= 5 && i < 17);
    group.add(joint);
    return joint;
  });
  const bones = edges.map(({ top, bottom }) => {
    const bone = new THREE.Mesh(
      new THREE.CylinderGeometry(top, bottom, 1, 10, 1),
      mat,
    );
    group.add(bone);
    return bone;
  });
  const torsoMat = mat.clone();
  const pelvisMat = mat.clone();
  if (opacity >= 1) {
    torsoMat.color.set("#2f936b");
    pelvisMat.color.set("#42574d");
  }
  const torso = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 18), torsoMat);
  group.add(torso);
  const pelvis = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 14), pelvisMat);
  group.add(pelvis);
  const headMat = mat.clone();
  headMat.roughness = 0.42;
  const head = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), headMat);
  group.add(head);
  const torsoDetails = new THREE.Group();
  const faceDetails = new THREE.Group();
  if (opacity >= 1) {
    const chestMark = new THREE.Mesh(
      new THREE.SphereGeometry(1, 16, 12),
      new THREE.MeshStandardMaterial({ color: "#f5d477", roughness: 0.4 }),
    );
    chestMark.position.set(0, 0.12, 0.94);
    chestMark.scale.set(0.19, 0.16, 0.045);
    torsoDetails.add(chestMark);
    const backSeam = new THREE.Mesh(
      new THREE.BoxGeometry(0.045, 0.95, 0.035),
      new THREE.MeshStandardMaterial({ color: "#173f32", roughness: 0.7 }),
    );
    backSeam.position.set(0, 0, -0.91);
    torsoDetails.add(backSeam);
    const eyeMat = new THREE.MeshStandardMaterial({
      color: "#26342f",
      roughness: 0.55,
    });
    for (const x of [-0.34, 0.34]) {
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 8), eyeMat);
      eye.position.set(x, 0.2, 1.02);
      eye.scale.set(0.7, 0.82, 0.34);
      faceDetails.add(eye);
    }
    const nose = new THREE.Mesh(
      new THREE.SphereGeometry(0.13, 12, 8),
      new THREE.MeshStandardMaterial({ color: "#c6a47f", roughness: 0.65 }),
    );
    nose.position.set(0, -0.015, 1.12);
    nose.scale.set(0.3, 0.31, 0.9);
    faceDetails.add(nose);
    const smile = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-0.19, -0.16, 1.02),
        new THREE.Vector3(0, -0.2, 1.1),
        new THREE.Vector3(0.19, -0.16, 1.02),
      ]),
      new THREE.LineBasicMaterial({ color: "#714f44" }),
    );
    faceDetails.add(smile);
  }
  group.add(torsoDetails, faceDetails);
  const racket = new THREE.Group();
  const frameMat = new THREE.MeshStandardMaterial({
    color: opacity < 1 ? "#80baff" : "#273b35",
    transparent: opacity < 1,
    opacity: opacity < 1 ? 0.78 : 1,
    roughness: 0.38,
    metalness: 0.28,
    depthWrite: opacity >= 1,
  });
  const racketPart = (
    radiusTop,
    radiusBottom,
    height,
    y,
    material = frameMat,
  ) => {
    const part = new THREE.Mesh(
      new THREE.CylinderGeometry(radiusTop, radiusBottom, height, 14),
      material,
    );
    part.position.y = y;
    racket.add(part);
  };
  racketPart(0.023, 0.026, 0.31, -0.15);
  racketPart(0.034, 0.023, 0.15, 0.075);
  const hoop = new THREE.Mesh(
    new THREE.TorusGeometry(0.19, 0.018, 8, 40),
    frameMat,
  );
  hoop.position.y = 0.34;
  hoop.scale.set(0.78, 1.08, 0.72);
  racket.add(hoop);
  const throat = new THREE.BufferGeometry();
  throat.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(
      [-0.09, 0.13, 0, -0.15, 0.31, 0, 0.09, 0.13, 0, 0.15, 0.31, 0],
      3,
    ),
  );
  racket.add(
    new THREE.LineSegments(
      throat,
      new THREE.LineBasicMaterial({
        color: opacity < 1 ? "#80baff" : "#273b35",
        transparent: opacity < 1,
        opacity: 0.9,
      }),
    ),
  );
  const stringMat = new THREE.LineBasicMaterial({
    color: opacity < 1 ? "#80baff" : "#d9eee3",
    transparent: opacity < 1,
    opacity: opacity < 1 ? 0.76 : 0.92,
    depthWrite: false,
  });
  const strings = [];
  for (let x = -0.12; x <= 0.1201; x += 0.04) {
    const y = 0.19 * Math.sqrt(1 - (x / 0.148) ** 2);
    strings.push(x, 0.34 - y, 0.008, x, 0.34 + y, 0.008);
  }
  for (let y = -0.15; y <= 0.1501; y += 0.05) {
    const x = 0.148 * Math.sqrt(1 - (y / 0.19) ** 2);
    strings.push(-x, 0.34 + y, 0.008, x, 0.34 + y, 0.008);
  }
  const stringBed = new THREE.BufferGeometry();
  stringBed.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(strings, 3),
  );
  racket.add(new THREE.LineSegments(stringBed, stringMat));
  const gripMat = new THREE.MeshStandardMaterial({
    color: opacity < 1 ? "#80baff" : "#e3d1ad",
    transparent: opacity < 1,
    opacity: opacity < 1 ? 0.8 : 1,
    roughness: 0.7,
    depthWrite: opacity >= 1,
  });
  racketPart(0.027, 0.023, 0.17, -0.18, gripMat);
  racket.visible = false;
  group.add(racket);
  const markers = [];
  for (let i = 0; i < 3; i += 1) {
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(1, 16, 12),
      new THREE.MeshBasicMaterial({
        color: "#8757e8",
        wireframe: true,
        transparent: true,
        opacity: 0.9,
        depthTest: false,
      }),
    );
    marker.scale.setScalar(0.105);
    marker.visible = false;
    group.add(marker);
    markers.push(marker);
  }
  playerStage.add(group);
  return {
    group,
    joints,
    bones,
    torso,
    pelvis,
    head,
    torsoDetails,
    faceDetails,
    racket,
    markers,
  };
}

const corrected = skeleton("#dfc6a4", 1);
const original = skeleton("#80baff", 0.58);
let data,
  frame = 0,
  playing = false,
  playbackSpeed = 1,
  lastTime = 0,
  accumulator = 0,
  scale = 1;
let racketWristIndex = 10;
let twoHandedGrip = false;
const scrub = document.getElementById("scrub");
const play = document.getElementById("play");
const axisY = new THREE.Vector3(0, 1, 0);

function positionBody(model, pose) {
  model.joints.forEach((joint, i) => {
    if (i === 17) {
      joint.position
        .copy(model.joints[5].position)
        .add(model.joints[6].position)
        .multiplyScalar(0.5);
    } else {
      joint.position.fromArray(pose[i]).multiplyScalar(scale);
    }
  });

  model.bones.forEach((bone, i) => {
    const { a, b } = edges[i];
    const start = model.joints[a].position;
    const end = model.joints[b].position;
    const vector = end.clone().sub(start);
    bone.position.copy(start).add(end).multiplyScalar(0.5);
    bone.scale.y = Math.max(vector.length(), 0.001);
    bone.quaternion.setFromUnitVectors(axisY, vector.normalize());
  });

  const shoulderCenter = model.joints[17].position;
  const hipCenter = model.joints[11].position
    .clone()
    .add(model.joints[12].position)
    .multiplyScalar(0.5);
  const torsoAxis = shoulderCenter.clone().sub(hipCenter);
  const shoulderWidth = model.joints[5].position.distanceTo(
    model.joints[6].position,
  );
  const torsoWidth = Math.max(shoulderWidth * 0.4, 0.09);
  model.torso.position.copy(shoulderCenter).add(hipCenter).multiplyScalar(0.5);
  const torsoUp = torsoAxis.clone().normalize();
  const torsoRight = model.joints[6].position
    .clone()
    .sub(model.joints[5].position);
  torsoRight.addScaledVector(torsoUp, -torsoRight.dot(torsoUp)).normalize();
  let torsoFront = torsoRight.clone().cross(torsoUp).normalize();
  const nose = model.joints[0].position.clone();
  const noseFront = nose.clone().sub(shoulderCenter);
  noseFront.addScaledVector(torsoUp, -noseFront.dot(torsoUp));
  if (noseFront.lengthSq() > 0.0001) {
    if (torsoFront.dot(noseFront) < 0) torsoFront.negate();
  } else if (torsoFront.z < 0) {
    torsoFront.negate();
  }
  const torsoRightOrtho = torsoUp.clone().cross(torsoFront).normalize();
  const torsoBasis = new THREE.Matrix4().makeBasis(
    torsoRightOrtho,
    torsoUp,
    torsoFront,
  );
  const torsoRotation = new THREE.Quaternion().setFromRotationMatrix(
    torsoBasis,
  );
  model.torso.quaternion.copy(torsoRotation);
  model.torso.scale.set(
    torsoWidth,
    Math.max(torsoAxis.length() * 0.56, 0.12),
    torsoWidth * 0.72,
  );
  model.torsoDetails.position.copy(model.torso.position);
  model.torsoDetails.quaternion.copy(torsoRotation);
  model.torsoDetails.scale.copy(model.torso.scale);

  const hipAxis = model.joints[12].position
    .clone()
    .sub(model.joints[11].position);
  const hipWidth = hipAxis.length();
  model.pelvis.position.copy(hipCenter);
  model.pelvis.quaternion.setFromUnitVectors(
    new THREE.Vector3(1, 0, 0),
    hipAxis.normalize(),
  );
  model.pelvis.scale.set(
    Math.max(hipWidth * 0.68, 0.12),
    0.105,
    Math.max(hipWidth * 0.4, 0.075),
  );

  const headDirection = nose.clone().sub(shoulderCenter).normalize();
  model.head.position.copy(nose).addScaledVector(headDirection, 0.07);
  model.head.scale.set(0.105, 0.135, 0.105);
  model.faceDetails.position.copy(model.head.position);
  model.faceDetails.quaternion.copy(torsoRotation);
  model.faceDetails.scale.copy(model.head.scale);

  const grip = twoHandedGrip
    ? model.joints[9].position
        .clone()
        .add(model.joints[10].position)
        .multiplyScalar(0.5)
    : model.joints[racketWristIndex].position.clone();
  const elbowIndex = racketWristIndex === 9 ? 7 : 8;
  const swingDirection = grip
    .clone()
    .sub(model.joints[elbowIndex].position);
  if (swingDirection.lengthSq() < 0.0001) swingDirection.set(0.7, 0.5, 0.2);
  swingDirection.normalize();
  model.racket.position
    .copy(grip)
    .addScaledVector(swingDirection, 0.1 * scale);
  model.racket.quaternion.setFromUnitVectors(axisY, swingDirection);
  model.racket.scale.setScalar(scale * 0.86);
  model.racket.visible = true;
}

function showPose(model, pose, focusIndices) {
  positionBody(model, pose);
  model.markers.forEach((marker, i) => {
    const index = focusIndices[i];
    marker.visible = index !== undefined;
    if (index !== undefined) {
      if (index === "hips") {
        marker.position
          .copy(model.joints[11].position)
          .add(model.joints[12].position)
          .multiplyScalar(0.5);
      } else {
        marker.position.copy(model.joints[index].position);
      }
    }
  });
}

function getFocusIndices() {
  const joints = data?.focus_joints ?? [];
  const indices = joints
    .map((joint) => focusJointIndices[joint])
    .filter(Number.isInteger);
  if (joints.includes("hip_rotation")) indices.push("hips");
  return indices.slice(0, 3);
}

function racketHandPosition(pose) {
  if (twoHandedGrip) {
    return new THREE.Vector3(
      (pose[9][0] + pose[10][0]) * 0.5,
      (pose[9][1] + pose[10][1]) * 0.5,
      (pose[9][2] + pose[10][2]) * 0.5,
    ).multiplyScalar(scale);
  }
  return new THREE.Vector3(...pose[racketWristIndex]).multiplyScalar(scale);
}

function drawFrame() {
  if (!data) return;
  const focusIndices = getFocusIndices();
  showPose(corrected, data.frames[frame], focusIndices);
  if (data.original_frames)
    showPose(original, data.original_frames[frame], focusIndices);
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
    const groundY =
      Math.min(...data.frames.map((pose) => Math.min(pose[15][1], pose[16][1]))) *
      scale;
    court.position.set(0, groundY, 0);
    groundShadow.position.y = groundY + 0.012;

    const wristTravel = (wristIndex) => {
      let distance = 0;
      for (let i = 1; i < data.frames.length; i += 1) {
        distance += new THREE.Vector3(...data.frames[i][wristIndex]).distanceTo(
          new THREE.Vector3(...data.frames[i - 1][wristIndex]),
        );
      }
      return distance;
    };
    racketWristIndex = wristTravel(9) > wristTravel(10) ? 9 : 10;
    const averageWristGap =
      data.frames.reduce(
        (total, pose) =>
          total +
          new THREE.Vector3(...pose[9]).distanceTo(new THREE.Vector3(...pose[10])),
        0,
      ) / data.frames.length;
    twoHandedGrip = averageWristGap < (Math.max(...ys) - Math.min(...ys)) * 0.1;

    const firstPose = data.frames[0];
    const point = (index) => new THREE.Vector3(...firstPose[index]);
    const up = point(5).add(point(6)).multiplyScalar(0.5)
      .sub(point(11).add(point(12)).multiplyScalar(0.5)).normalize();
    const right = point(6).sub(point(5));
    right.addScaledVector(up, -right.dot(up)).normalize();
    const front = right.clone().cross(up).normalize();
    const noseFront = point(0).sub(point(5).add(point(6)).multiplyScalar(0.5));
    noseFront.addScaledVector(up, -noseFront.dot(up));
    if (noseFront.lengthSq() > 0.0001 && front.dot(noseFront) < 0) {
      front.negate();
    }
    if (front.lengthSq() > 0.0001) {
      playerStage.rotation.y = Math.atan2(-front.x, front.z);
    }

    const trail = data.frames.map(racketHandPosition);
    const trailCurve = new THREE.CatmullRomCurve3(trail);
    racketPathGeometry.setFromPoints(
      trailCurve.getPoints(Math.max(48, data.frames.length * 2)),
    );
    racketPathGeometry.computeBoundingSphere();

    // Contact is an estimated phase within this window, not a source-video index.
    frame =
      Number.isInteger(data.contact_frame) &&
      data.contact_frame >= 0 &&
      data.contact_frame < data.frames.length
        ? data.contact_frame
        : 0;
    playing = false;
    accumulator = 0;
    play.textContent = "Play";
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
const speedControl = document.getElementById("speed");
speedControl.onchange = () => {
  playbackSpeed = Number(speedControl.value);
  accumulator = 0;
};
document.getElementById("reset").onclick = () => {
  camera.position.copy(frontCameraPosition);
  controls.target.copy(frontCameraTarget);
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
    accumulator += Math.min(time - lastTime, 100) * playbackSpeed;
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
