import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';

export type AuthStackParams = {
  Welcome: undefined;
  Login: undefined;
  Signup: undefined;
};

export type MainTabParams = {
  Home: undefined;
  Record: undefined;
  Profile: undefined;
};

export type RecordingStackParams = {
  Record: undefined;
  UploadProgress: { videoUri: string };
  Result: { jobId: string };
};

export type AuthScreenProps<T extends keyof AuthStackParams> =
  NativeStackScreenProps<AuthStackParams, T>;

export type RecordingScreenProps<T extends keyof RecordingStackParams> =
  NativeStackScreenProps<RecordingStackParams, T>;
