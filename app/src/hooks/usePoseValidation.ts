import { useMemo } from 'react';

export interface PoseValidationResult {
  isValid: boolean;
  allVisible: boolean;
  isSideOn: boolean;
  isCorrectDistance: boolean;
  instructionText: string;
}

interface Keypoint {
  x: number;
  y: number;
  score?: number;
}

const LEFT_SHOULDER = 5;
const RIGHT_SHOULDER = 6;
const LEFT_HIP = 11;
const RIGHT_HIP = 12;
const NOSE = 0;
const LEFT_ANKLE = 15;
const RIGHT_ANKLE = 16;

export function usePoseValidation(pose: Keypoint[] | null): PoseValidationResult {
  return useMemo(() => {
    const invalid = (msg: string): PoseValidationResult => ({
      isValid: false,
      allVisible: false,
      isSideOn: false,
      isCorrectDistance: false,
      instructionText: msg,
    });

    if (!pose || pose.length < 17) {
      return invalid('Position yourself in the frame');
    }

    const keyJoints = [NOSE, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP, LEFT_ANKLE, RIGHT_ANKLE];
    const allVisible = keyJoints.every((i) => (pose[i]?.score ?? 0) > 0.4);

    if (!allVisible) {
      return { ...invalid('Make sure your full body is visible'), allVisible: false };
    }

    // Side-on: shoulders should be close in x (one in front of the other, not spread)
    const shoulderSep = Math.abs(pose[LEFT_SHOULDER].x - pose[RIGHT_SHOULDER].x);
    const isSideOn = shoulderSep < 0.15;

    if (!isSideOn) {
      return { isValid: false, allVisible: true, isSideOn: false, isCorrectDistance: false, instructionText: 'Turn to face sideways' };
    }

    // Distance: hip depth in normalized coords
    const hipWidth = Math.abs(pose[LEFT_HIP].x - pose[RIGHT_HIP].x);
    const isCorrectDistance = hipWidth > 0.02 && hipWidth < 0.15;

    if (!isCorrectDistance) {
      const msg = hipWidth < 0.02 ? 'Step closer to the camera' : 'Step further from the camera';
      return { isValid: false, allVisible: true, isSideOn: true, isCorrectDistance: false, instructionText: msg };
    }

    return { isValid: true, allVisible: true, isSideOn: true, isCorrectDistance: true, instructionText: 'Hold still - ready to record!' };
  }, [pose]);
}
