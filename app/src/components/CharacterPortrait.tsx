import React from "react";
import { Image, ImageStyle, StyleProp, StyleSheet, View } from "react-native";

const characters = {
  pipkin: {
    name: "Pipkin",
    color: "#E8A07A",
    image: require("../../assets/characters/pipkin.jpg"),
  },
  marlow: {
    name: "Marlow",
    color: "#7EA7D6",
    image: require("../../assets/characters/marlow.jpg"),
  },
  patch: {
    name: "Patch",
    color: "#5BB8A0",
    image: require("../../assets/characters/patch.jpg"),
  },
} as const;

export type CharacterName = keyof typeof characters;

export function CharacterPortrait({
  character,
  size = 64,
  style,
}: {
  character: CharacterName;
  size?: number;
  style?: StyleProp<ImageStyle>;
}) {
  const details = characters[character];
  return (
    <View
      accessibilityRole="image"
      accessibilityLabel={details.name}
      style={[
        styles.frame,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          borderColor: details.color,
        },
      ]}
    >
      <Image
        accessible={false}
        source={details.image}
        resizeMode="cover"
        style={[styles.image, { width: size - 4, height: size - 4 }, style]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    borderWidth: 2,
    overflow: "hidden",
    backgroundColor: "#FFFFFF",
  },
  image: { borderRadius: 999 },
});
