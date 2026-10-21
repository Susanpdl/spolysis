package com.spolysis.pose;
import com.mrousavy.camera.frameprocessors.Frame;
import com.mrousavy.camera.frameprocessors.FrameProcessorPlugin;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.pose.Pose;
import com.google.mlkit.vision.pose.PoseDetector;
import com.google.mlkit.vision.pose.PoseDetection;
import com.google.mlkit.vision.pose.PoseLandmark;
import com.google.mlkit.vision.pose.defaults.PoseDetectorOptions;
import com.google.android.gms.tasks.Tasks;
import java.util.*;

public class PosePlugin extends FrameProcessorPlugin {
  private final PoseDetector detector = PoseDetection.getClient(new PoseDetectorOptions.Builder().setDetectorMode(PoseDetectorOptions.STREAM_MODE).build());
  private final int[] indices = {0,2,5,7,8,11,12,13,14,15,16,23,24,25,26,27,28};
  @Override public Object callback(Frame frame, Map<String,Object> arguments) throws Throwable {
    int rotation = frame.getImageProxy().getImageInfo().getRotationDegrees();
    InputImage image = InputImage.fromMediaImage(frame.getImage(), rotation);
    Pose pose = Tasks.await(detector.process(image));
    boolean sideways = rotation == 90 || rotation == 270;
    double width = sideways ? frame.getHeight() : frame.getWidth();
    double height = sideways ? frame.getWidth() : frame.getHeight();
    List<Map<String,Object>> output = new ArrayList<>();
    for (int index : indices) {
      PoseLandmark point = pose.getPoseLandmark(index);
      if (point == null) return Collections.emptyList();
      Map<String,Object> value = new HashMap<>();
      value.put("x", (double)point.getPosition().x / width);
      value.put("y", (double)point.getPosition().y / height);
      value.put("score", (double)point.getInFrameLikelihood());
      output.add(value);
    }
    return output;
  }
}
