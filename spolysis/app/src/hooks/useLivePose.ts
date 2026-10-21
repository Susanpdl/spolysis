import { useMemo, useState, useEffect } from "react";
import {
  VisionCameraProxy,
  useFrameProcessor,
  runAtTargetFps,
} from "react-native-vision-camera";
import { Worklets } from "react-native-worklets-core";

export interface Keypoint {
  x: number;
  y: number;
  score: number;
}
export function useLivePose(enabled: boolean) {
  const [sample, setSample] = useState<{
    pose: Keypoint[];
    time: number;
  } | null>(null);
  const [now, setNow] = useState(Date.now());
  const plugin = useMemo(
    () => VisionCameraProxy.initFrameProcessorPlugin("spolysisPose", {}),
    [],
  );
  const onPose = useMemo(
    () =>
      Worklets.createRunOnJS((pose: Keypoint[]) =>
        setSample({ pose, time: Date.now() }),
      ),
    [],
  );
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, []);
  const frameProcessor = useFrameProcessor(
    (frame) => {
      "worklet";
      if (!enabled || !plugin) return;
      runAtTargetFps(3, () => {
        "worklet";
        const result = plugin.call(frame) as unknown as Keypoint[];
        onPose(result);
      });
    },
    [plugin, enabled, onPose],
  );
  return {
    frameProcessor,
    pose: sample && now - sample.time < 1500 ? sample.pose : null,
    available: !!plugin,
  };
}
