require 'xcodeproj'

path = ARGV.fetch(0, '/tmp/SpolysisUITests.xcodeproj')
project = Xcodeproj::Project.new(path)
target = project.new_target(:ui_test_bundle, 'SpolysisUITests', :ios, '16.0')
file = project.main_group.new_file(File.join(__dir__, 'SmokeTests.swift'))
target.source_build_phase.add_file_reference(file)
target.build_configurations.each do |config|
  config.build_settings['PRODUCT_BUNDLE_IDENTIFIER'] = 'com.spolysis.uitests'
  config.build_settings['GENERATE_INFOPLIST_FILE'] = 'YES'
  config.build_settings['SWIFT_VERSION'] = '5.0'
  config.build_settings['CODE_SIGNING_ALLOWED'] = 'NO'
end
scheme = Xcodeproj::XCScheme.new
scheme.add_build_target(target)
scheme.add_test_target(target)
scheme.save_as(path, 'SpolysisUITests', true)
project.save
puts path
