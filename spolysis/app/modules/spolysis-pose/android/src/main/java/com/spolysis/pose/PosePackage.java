package com.spolysis.pose;
import com.facebook.react.ReactPackage;
import com.facebook.react.bridge.NativeModule;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.uimanager.ViewManager;
import com.mrousavy.camera.frameprocessors.FrameProcessorPluginRegistry;
import java.util.Collections;
import java.util.List;

public class PosePackage implements ReactPackage {
  static { FrameProcessorPluginRegistry.addFrameProcessorPlugin("spolysisPose", (proxy, options) -> new PosePlugin()); }
  @Override public List<NativeModule> createNativeModules(ReactApplicationContext context) { return Collections.emptyList(); }
  @Override public List<ViewManager> createViewManagers(ReactApplicationContext context) { return Collections.emptyList(); }
}
