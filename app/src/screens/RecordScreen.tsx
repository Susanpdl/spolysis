import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Alert,
  Platform,
} from 'react-native';
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  useFrameProcessor,
} from 'react-native-vision-camera';
import { useSharedValue, runOnJS } from 'react-native-reanimated';
import PoseDetection, {
  type PoseDetectionResult,
} from '@react-native-ml-kit/pose-detection';
import { RecordingScreenProps } from '@/navigation/types';
import { BodyOutline } from '@/components/BodyOutline';
import { usePoseValidation } from '@/hooks/usePoseValidation';
import { recordingStore } from '@/store/recordingStore';
import { colors, typography, spacing } from '@/theme';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');
const OUTLINE_W = SCREEN_W * 0.55;
const OUTLINE_H = SCREEN_H * 0.72;
const MAX_DURATION_SEC = 300; // 5 min

type RecordingPhase = 'preview' | 'countdown' | 'recording' | 'stopping';

function useCountdown(from: number, onDone: () => void) {
  const [count, setCount] = useState(from);
  const active = useRef(false);

  const start = useCallback(() => {
    active.current = true;
    setCount(from);
  }, [from]);

  useEffect(() => {
    if (!active.current || count <= 0) {
      if (count <= 0 && active.current) {
        active.current = false;
        onDone();
      }
      return;
    }
    const t = setTimeout(() => setCount((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [count, onDone]);

  return { count, start };
}

export default function RecordScreen({ navigation }: RecordingScreenProps<'Record'>) {
  const { hasPermission, requestPermission } = useCameraPermission();
  const device = useCameraDevice('back');
  const cameraRef = useRef<Camera>(null);

  const [phase, setPhase] = useState<RecordingPhase>('preview');
  const [elapsedSec, setElapsedSec] = useState(0);
  const [pose, setPose] = useState<Array<{ x: number; y: number; score?: number }> | null>(null);

  const { isValid, instructionText } = usePoseValidation(pose);
  const { setVideoUri } = recordingStore();

  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const frameSkip = useRef(0);

  const updatePose = useCallback((result: PoseDetectionResult | null) => {
    if (!result || result.poses.length === 0) {
      setPose(null);
      return;
    }
    const kps = result.poses[0].keypoints.map((kp) => ({
      x: kp.x / SCREEN_W,
      y: kp.y / SCREEN_H,
      score: kp.score ?? 0,
    }));
    setPose(kps);
  }, []);

  // Frame processor runs on GPU thread; we throttle to every 6th frame (~5 fps at 30fps input)
  const frameProcessor = useFrameProcessor(
    (frame) => {
      'worklet';
      frameSkip.current = (frameSkip.current + 1) % 6;
      if (frameSkip.current !== 0) return;
      const result = PoseDetection.detectFromVisionCameraFrame(frame);
      runOnJS(updatePose)(result as PoseDetectionResult | null);
    },
    [updatePose],
  );

  const startRecording = useCallback(async () => {
    if (!cameraRef.current) return;
    setPhase('recording');
    setElapsedSec(0);

    elapsedRef.current = setInterval(() => {
      setElapsedSec((s) => {
        if (s + 1 >= MAX_DURATION_SEC) {
          stopRecording();
        }
        return s + 1;
      });
    }, 1000);

    cameraRef.current.startRecording({
      fileType: 'mp4',
      onRecordingFinished: (video) => {
        setVideoUri(video.path);
        navigation.navigate('UploadProgress', { videoUri: video.path });
      },
      onRecordingError: (err) => {
        setPhase('preview');
        Alert.alert('Recording failed', err.message);
      },
    });
  }, [navigation, setVideoUri]);

  const stopRecording = useCallback(async () => {
    if (elapsedRef.current) {
      clearInterval(elapsedRef.current);
      elapsedRef.current = null;
    }
    setPhase('stopping');
    await cameraRef.current?.stopRecording();
  }, []);

  const { count, start: startCountdown } = useCountdown(3, startRecording);

  const handleRecordPress = () => {
    if (phase === 'preview') {
      if (!isValid) {
        Alert.alert('Not ready', instructionText);
        return;
      }
      setPhase('countdown');
      startCountdown();
    } else if (phase === 'recording') {
      stopRecording();
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (elapsedRef.current) clearInterval(elapsedRef.current);
    };
  }, []);

  // Permission gate
  useEffect(() => {
    if (!hasPermission) requestPermission();
  }, [hasPermission, requestPermission]);

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  };

  if (!hasPermission) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={[typography.body, { color: colors.text.secondary, textAlign: 'center' }]}>
          Camera access is required to record your stroke.
        </Text>
        <TouchableOpacity onPress={requestPermission} style={styles.permissionBtn}>
          <Text style={{ color: colors.primary, fontWeight: '600' }}>Grant access</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!device) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={[typography.body, { color: colors.text.secondary }]}>No camera found.</Text>
      </View>
    );
  }

  const isRecording = phase === 'recording';
  const isCountdown = phase === 'countdown';

  return (
    <View style={styles.container}>
      <Camera
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        device={device}
        isActive
        video
        audio={false}
        frameProcessor={phase === 'preview' || phase === 'countdown' ? frameProcessor : undefined}
      />

      {/* Body outline overlay */}
      <View style={styles.outlineWrap} pointerEvents="none">
        <BodyOutline width={OUTLINE_W} height={OUTLINE_H} valid={isValid} />
      </View>

      {/* Top bar */}
      <View style={styles.topBar}>
        {isRecording ? (
          <View style={styles.recIndicator}>
            <View style={styles.recDot} />
            <Text style={styles.recTimer}>{formatElapsed(elapsedSec)}</Text>
          </View>
        ) : (
          <View style={styles.instructionPill}>
            <Text style={styles.instructionText} numberOfLines={1}>
              {isCountdown ? `Starting in ${count}...` : instructionText}
            </Text>
          </View>
        )}
      </View>

      {/* Bottom controls */}
      <View style={styles.bottomBar}>
        {!isRecording && !isCountdown && (
          <Text style={[typography.caption, styles.hint]}>
            Stand side-on, full body visible.
            {'\n'}Max 5 minutes.
          </Text>
        )}
        <TouchableOpacity
          style={[
            styles.recordBtn,
            isRecording && styles.recordBtnStop,
            isCountdown && styles.recordBtnDisabled,
          ]}
          onPress={handleRecordPress}
          disabled={isCountdown || phase === 'stopping'}
          activeOpacity={0.8}
        >
          {isRecording ? (
            <View style={styles.stopSquare} />
          ) : (
            <View style={[styles.recordCircle, isValid && styles.recordCircleReady]} />
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  permissionContainer: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.lg,
    padding: spacing.xl,
  },
  permissionBtn: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  outlineWrap: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
  },
  topBar: {
    position: 'absolute',
    top: 60,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  instructionPill: {
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 20,
    maxWidth: 280,
  },
  instructionText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  recIndicator: {
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  recDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.error,
  },
  recTimer: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
  },
  bottomBar: {
    position: 'absolute',
    bottom: 60,
    left: 0,
    right: 0,
    alignItems: 'center',
    gap: spacing.md,
  },
  hint: {
    color: 'rgba(255,255,255,0.7)',
    textAlign: 'center',
    lineHeight: 18,
  },
  recordBtn: {
    width: 76,
    height: 76,
    borderRadius: 38,
    borderWidth: 4,
    borderColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.3)',
  },
  recordBtnStop: {
    borderColor: colors.error,
  },
  recordBtnDisabled: {
    opacity: 0.5,
  },
  recordCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: '#fff',
  },
  recordCircleReady: {
    backgroundColor: colors.primary,
  },
  stopSquare: {
    width: 28,
    height: 28,
    borderRadius: 6,
    backgroundColor: colors.error,
  },
});
