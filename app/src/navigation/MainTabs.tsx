import React from "react";
import Svg, { Path, Circle, Rect } from "react-native-svg";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { MainTabParams } from "./types";
import { RecordingStack } from "./RecordingStack";
import HomeScreen from "@/screens/HomeScreen";
import ProfileScreen from "@/screens/ProfileScreen";
import { colors } from "@/theme";

const Tab = createBottomTabNavigator<MainTabParams>();

export function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ color, size }) => (
          <Svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke={color}
            strokeWidth={1.7}
          >
            {route.name === "Home" ? (
              <>
                <Rect x={4} y={3} width={16} height={18} rx={3} />
                <Path d="M8 8h8M8 12h8M8 16h5" />
              </>
            ) : route.name === "Record" ? (
              <>
                <Rect x={3} y={6} width={18} height={15} rx={4} />
                <Circle cx={12} cy={13} r={4} />
                <Path d="M8 6l1-3h6l1 3" />
              </>
            ) : (
              <>
                <Circle cx={12} cy={8} r={4} />
                <Path d="M4 22v-2a8 8 0 0116 0v2" />
              </>
            )}
          </Svg>
        ),
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: 82,
          paddingTop: 9,
          paddingBottom: 12,
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.text.muted,
        tabBarLabelStyle: {
          fontFamily: "DMSans_600SemiBold",
          fontSize: 11,
        },
      })}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{ tabBarLabel: "Analyses" }}
      />
      <Tab.Screen
        name="Record"
        component={RecordingStack}
        options={{ tabBarLabel: "Record" }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ tabBarLabel: "Profile" }}
      />
    </Tab.Navigator>
  );
}
