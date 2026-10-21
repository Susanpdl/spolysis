Pod::Spec.new do |s|
  s.name = 'SpolysisPose'
  s.version = '1.0.0'
  s.summary = 'Live body framing with Apple Vision'
  s.homepage = 'https://github.com/Susanpdl/spolysis'
  s.license = 'MIT'
  s.author = 'Spolysis'
  s.source = { :git => 'https://github.com/Susanpdl/spolysis.git' }
  s.platforms = { :ios => '13.4' }
  s.source_files = 'ios/**/*.{h,m,mm}'
  s.frameworks = 'Vision', 'ImageIO'
  s.dependency 'VisionCamera'
end
