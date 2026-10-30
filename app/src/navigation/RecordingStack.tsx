import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { RecordingStackParams } from "./types";
import RecordScreen from "@/screens/RecordScreen";
import UploadProgressScreen from "@/screens/UploadProgressScreen";
import ResultScreen from "@/screens/ResultScreen";

const Stack = createNativeStackNavigator<RecordingStackParams>();

export function RecordingStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Capture" component={RecordScreen} />
      <Stack.Screen
        name="UploadProgress"
        component={UploadProgressScreen}
        getId={({ params }) => params.jobId ?? params.videoUri}
      />
      <Stack.Screen
        name="Result"
        component={ResultScreen}
        getId={({ params }) => params.jobId}
        options={{ gestureEnabled: false }}
      />
    </Stack.Navigator>
  );
}
