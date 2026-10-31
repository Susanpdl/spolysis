import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { RecordingStackParams } from "./types";
import RecordScreen from "@/screens/RecordScreen";
import UploadProgressScreen from "@/screens/UploadProgressScreen";
import ResultScreen from "@/screens/ResultScreen";
import SportSelectionScreen from "@/screens/SportSelectionScreen";

const Stack = createNativeStackNavigator<RecordingStackParams>();

export function RecordingStack() {
  return (
    <Stack.Navigator
      initialRouteName="Sports"
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen name="Sports" component={SportSelectionScreen} />
      <Stack.Screen
        name="Capture"
        component={RecordScreen}
        getId={({ params }) => params.sportId}
      />
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
