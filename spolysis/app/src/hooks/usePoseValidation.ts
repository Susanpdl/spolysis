import { useMemo } from "react";
interface Keypoint {
  x: number;
  y: number;
  score?: number;
}
export interface PoseValidationResult {
  isValid: boolean;
  allVisible: boolean;
  isSideOn: boolean;
  isCorrectDistance: boolean;
  instructionText: string;
}
export function validatePose(pose: Keypoint[] | null): PoseValidationResult {
  const fail = (instructionText: string): PoseValidationResult => ({
    isValid: false,
    allVisible: false,
    isSideOn: false,
    isCorrectDistance: false,
    instructionText,
  });
  if (!pose || pose.length < 17)
    return fail("Stand in view with your whole body visible");
  const required = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
  if (
    required.some(
      (i) =>
        (pose[i].score ?? 0) < 0.35 ||
        !Number.isFinite(pose[i].x) ||
        !Number.isFinite(pose[i].y),
    )
  )
    return fail("Keep your head, hands and feet visible");
  if (
    required.some(
      (i) =>
        pose[i].x < 0.03 ||
        pose[i].x > 0.97 ||
        pose[i].y < 0.03 ||
        pose[i].y > 0.97,
    )
  )
    return fail("Step back so your whole body fits");
  const height = Math.max(pose[15].y, pose[16].y) - pose[0].y;
  if (height < 0.4) return fail("Move closer to the camera");
  if (height > 0.88) return fail("Step back a little");
  const separation = Math.abs(pose[5].x - pose[6].x) / height;
  if (separation > 0.34)
    return fail("Turn slightly sideways toward your hitting direction");
  return {
    isValid: true,
    allVisible: true,
    isSideOn: true,
    isCorrectDistance: true,
    instructionText: "Framing ready. Tap record and prepare your stroke.",
  };
}
export function usePoseValidation(pose: Keypoint[] | null) {
  return useMemo(() => validatePose(pose), [pose]);
}
