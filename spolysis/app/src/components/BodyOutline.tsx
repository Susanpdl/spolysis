import React from 'react';
import Svg, { Circle, Line } from 'react-native-svg';
import { colors } from '@/theme';

interface BodyOutlineProps {
  width: number;
  height: number;
  valid: boolean;
}

export function BodyOutline({ width, height, valid }: BodyOutlineProps) {
  const stroke = valid ? colors.stroke.valid : colors.stroke.invalid;
  const sw = 2.5;
  const opacity = 0.75;

  // Design in 100x220 units, scale to actual dimensions
  const sx = (x: number) => (x / 100) * width;
  const sy = (y: number) => (y / 220) * height;

  return (
    <Svg width={width} height={height} opacity={opacity}>
      {/* Head */}
      <Circle cx={sx(50)} cy={sy(16)} r={sx(12)} stroke={stroke} strokeWidth={sw} fill="none" />
      {/* Neck */}
      <Line x1={sx(50)} y1={sy(28)} x2={sx(50)} y2={sy(38)} stroke={stroke} strokeWidth={sw} />
      {/* Shoulders */}
      <Line x1={sx(22)} y1={sy(42)} x2={sx(78)} y2={sy(42)} stroke={stroke} strokeWidth={sw} />
      {/* Torso sides */}
      <Line x1={sx(35)} y1={sy(42)} x2={sx(35)} y2={sy(105)} stroke={stroke} strokeWidth={sw} />
      <Line x1={sx(65)} y1={sy(42)} x2={sx(65)} y2={sy(105)} stroke={stroke} strokeWidth={sw} />
      {/* Waist */}
      <Line x1={sx(35)} y1={sy(105)} x2={sx(65)} y2={sy(105)} stroke={stroke} strokeWidth={sw} />
      {/* Left arm */}
      <Line x1={sx(22)} y1={sy(42)} x2={sx(10)} y2={sy(70)} stroke={stroke} strokeWidth={sw} />
      <Line x1={sx(10)} y1={sy(70)} x2={sx(8)} y2={sy(95)} stroke={stroke} strokeWidth={sw} />
      {/* Right arm */}
      <Line x1={sx(78)} y1={sy(42)} x2={sx(88)} y2={sy(68)} stroke={stroke} strokeWidth={sw} />
      <Line x1={sx(88)} y1={sy(68)} x2={sx(92)} y2={sy(93)} stroke={stroke} strokeWidth={sw} />
      {/* Hip joints */}
      <Line x1={sx(35)} y1={sy(105)} x2={sx(28)} y2={sy(108)} stroke={stroke} strokeWidth={sw} />
      <Line x1={sx(65)} y1={sy(105)} x2={sx(72)} y2={sy(108)} stroke={stroke} strokeWidth={sw} />
      {/* Left leg */}
      <Line x1={sx(28)} y1={sy(108)} x2={sx(24)} y2={sy(158)} stroke={stroke} strokeWidth={sw} />
      <Line x1={sx(24)} y1={sy(158)} x2={sx(22)} y2={sy(205)} stroke={stroke} strokeWidth={sw} />
      {/* Right leg */}
      <Line x1={sx(72)} y1={sy(108)} x2={sx(76)} y2={sy(158)} stroke={stroke} strokeWidth={sw} />
      <Line x1={sx(76)} y1={sy(158)} x2={sx(78)} y2={sy(205)} stroke={stroke} strokeWidth={sw} />
      {/* Feet */}
      <Line x1={sx(22)} y1={sy(205)} x2={sx(14)} y2={sy(210)} stroke={stroke} strokeWidth={sw} />
      <Line x1={sx(78)} y1={sy(205)} x2={sx(86)} y2={sy(210)} stroke={stroke} strokeWidth={sw} />
    </Svg>
  );
}
