#import <VisionCamera/FrameProcessorPlugin.h>
#import <VisionCamera/Frame.h>
#import <Vision/Vision.h>
#import <ImageIO/ImageIO.h>

@interface SpolysisPosePlugin : FrameProcessorPlugin
@end

@implementation SpolysisPosePlugin
VISION_EXPORT_FRAME_PROCESSOR(SpolysisPosePlugin, spolysisPose)

- (id)callback:(Frame *)frame withArguments:(NSDictionary *)arguments {
  if (@available(iOS 14.0, *)) {
    CGImagePropertyOrientation orientation = kCGImagePropertyOrientationUp;
    switch (frame.orientation) {
      case UIImageOrientationDown: orientation = kCGImagePropertyOrientationDown; break;
      case UIImageOrientationLeft: orientation = kCGImagePropertyOrientationLeft; break;
      case UIImageOrientationRight: orientation = kCGImagePropertyOrientationRight; break;
      case UIImageOrientationUpMirrored: orientation = kCGImagePropertyOrientationUpMirrored; break;
      case UIImageOrientationDownMirrored: orientation = kCGImagePropertyOrientationDownMirrored; break;
      case UIImageOrientationLeftMirrored: orientation = kCGImagePropertyOrientationLeftMirrored; break;
      case UIImageOrientationRightMirrored: orientation = kCGImagePropertyOrientationRightMirrored; break;
      default: break;
    }
    VNDetectHumanBodyPoseRequest *request = [VNDetectHumanBodyPoseRequest new];
    VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCMSampleBuffer:frame.buffer orientation:orientation options:@{}];
    NSError *error = nil;
    if (![handler performRequests:@[request] error:&error] || request.results.count != 1) return @[];
    VNHumanBodyPoseObservation *pose = request.results.firstObject;
    NSArray *names = @[
      VNHumanBodyPoseObservationJointNameNose, VNHumanBodyPoseObservationJointNameNose,
      VNHumanBodyPoseObservationJointNameNose, VNHumanBodyPoseObservationJointNameNose,
      VNHumanBodyPoseObservationJointNameNose,
      VNHumanBodyPoseObservationJointNameLeftShoulder, VNHumanBodyPoseObservationJointNameRightShoulder,
      VNHumanBodyPoseObservationJointNameLeftElbow, VNHumanBodyPoseObservationJointNameRightElbow,
      VNHumanBodyPoseObservationJointNameLeftWrist, VNHumanBodyPoseObservationJointNameRightWrist,
      VNHumanBodyPoseObservationJointNameLeftHip, VNHumanBodyPoseObservationJointNameRightHip,
      VNHumanBodyPoseObservationJointNameLeftKnee, VNHumanBodyPoseObservationJointNameRightKnee,
      VNHumanBodyPoseObservationJointNameLeftAnkle, VNHumanBodyPoseObservationJointNameRightAnkle];
    NSMutableArray *output = [NSMutableArray new];
    for (NSString *name in names) {
      VNRecognizedPoint *point = [pose recognizedPointForJointName:name error:&error];
      [output addObject:@{@"x": @(point ? point.location.x : 0),
                          @"y": @(point ? 1 - point.location.y : 0),
                          @"score": @(point ? point.confidence : 0)}];
    }
    return output;
  }
  return @[];
}
@end
