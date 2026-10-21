import type { NavigatorScreenParams } from "@react-navigation/native";
import type { StrokeType } from "@/services/api";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

export type AuthStackParams = {
  Welcome: undefined;
  Login: undefined;
  Signup: undefined;
};

export type MainTabParams = {
  Home: undefined;
  Record: NavigatorScreenParams<RecordingStackParams>;
  Profile: undefined;
};

export type RecordingStackParams = {
  Capture: undefined;
  UploadProgress: {
    videoUri?: string;
    jobId?: string;
    strokeType?: StrokeType;
    handedness?: "right" | "left";
    contentType?: string;
  };
  Result: { jobId: string };
};

export type AuthScreenProps<T extends keyof AuthStackParams> =
  NativeStackScreenProps<AuthStackParams, T>;

export type RecordingScreenProps<T extends keyof RecordingStackParams> =
  NativeStackScreenProps<RecordingStackParams, T>;
