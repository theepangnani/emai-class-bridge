#!/bin/bash

# Script to create all GitHub issues for mobile app development
# Run with: bash scripts/create_mobile_issues.sh

echo "Creating GitHub issues for mobile app development..."
echo "This will create 42 issues in total."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# Phase 1: Backend API Preparation (12 issues)

echo "Creating Phase 1: Backend API issues..."

gh issue create \
  --title "Implement API Versioning (v1)" \
  --label "backend,api,breaking-change,mobile-prep,priority:high" \
  --body "## Description
Implement API versioning to support mobile apps that can't update instantly like web apps. Create \`/api/v1\` structure while maintaining backward compatibility with existing web app.

## Acceptance Criteria
- [ ] Create \`app/api/v1/\` directory structure
- [ ] Copy all existing routes to \`app/api/v1/routes/\`
- [ ] Update route prefixes (remove prefix from individual routers)
- [ ] Create \`app/api/v1/__init__.py\` router aggregator
- [ ] Mount v1 API at \`/api/v1\` in \`main.py\`
- [ ] Keep legacy \`/api\` routes for web (temporary)
- [ ] Update Swagger docs to show both versions
- [ ] All v1 endpoints tested and working

## Dependencies
None - can start immediately

## Estimated Effort
2 days

## Implementation Guide
See \`MOBILE_IMPLEMENTATION_PLAN.md\` → Phase 1, Week 1, Day 1-2"

gh issue create \
  --title "Add Pagination to All List Endpoints" \
  --label "backend,api,enhancement,mobile-prep,priority:high" \
  --body "## Description
Add pagination support to all list endpoints to optimize mobile bandwidth and battery usage. Implement consistent pagination pattern across all endpoints.

## Acceptance Criteria
- [ ] Create \`app/schemas/pagination.py\` with \`PaginatedResponse\` generic schema
- [ ] Add pagination to \`GET /api/v1/courses\` (skip, limit, has_more)
- [ ] Add pagination to \`GET /api/v1/assignments\`
- [ ] Add pagination to \`GET /api/v1/messages\`
- [ ] Add pagination to \`GET /api/v1/notifications\`
- [ ] Add pagination to \`GET /api/v1/students\` (for teachers/parents)
- [ ] Default limit: 20, max limit: 100
- [ ] Response format: \`{items: [...], total: N, skip: 0, limit: 20, has_more: bool}\`
- [ ] Update API tests to verify pagination
- [ ] Document pagination in Swagger

## Dependencies
Requires API versioning to be completed first

## Estimated Effort
2 days

## Example Response
\`\`\`json
{
  \"items\": [...],
  \"total\": 150,
  \"skip\": 0,
  \"limit\": 20,
  \"has_more\": true
}
\`\`\`"

gh issue create \
  --title "Implement Structured Error Responses" \
  --label "backend,api,enhancement,mobile-prep,priority:medium" \
  --body "## Description
Implement structured error responses with error codes and request IDs for better mobile error handling and debugging.

## Acceptance Criteria
- [ ] Create \`app/schemas/error.py\` with \`ErrorDetail\` and \`ErrorResponse\` models
- [ ] Create \`app/core/error_handlers.py\` with custom exception handler
- [ ] Register exception handler in \`main.py\`
- [ ] Update all endpoints to use structured errors
- [ ] All errors include \`request_id\` for debugging
- [ ] Update API documentation
- [ ] Test error responses

## Dependencies
Requires API versioning to be completed first

## Estimated Effort
1-2 days

## Example Error Response
\`\`\`json
{
  \"error\": {
    \"code\": \"AUTH_INVALID_CREDENTIALS\",
    \"message\": \"Invalid email or password\"
  },
  \"request_id\": \"550e8400-e29b-41d4-a716-446655440000\"
}
\`\`\`"

gh issue create \
  --title "Set Up Firebase Admin SDK for Push Notifications" \
  --label "backend,infrastructure,push-notifications,mobile-prep,priority:high" \
  --body "## Description
Set up Firebase Admin SDK on the backend to enable push notifications to mobile apps.

## Acceptance Criteria
- [ ] Create Firebase project in Firebase Console
- [ ] Add iOS app (\`com.classbridge.app\`)
- [ ] Add Android app (\`com.classbridge.app\`)
- [ ] Download service account key
- [ ] Add to \`.gitignore\`
- [ ] Install \`firebase-admin\` package
- [ ] Create \`app/core/firebase.py\` initialization module
- [ ] Initialize Firebase in \`main.py\` startup event
- [ ] Add \`FIREBASE_CREDENTIALS\` env var to \`.env.example\`
- [ ] Document Firebase setup in README
- [ ] Verify Firebase initializes without errors

## Dependencies
None - can start immediately

## Estimated Effort
1 day"

gh issue create \
  --title "Create DeviceToken Model and Registration Endpoints" \
  --label "backend,database,api,push-notifications,mobile-prep,priority:high" \
  --body "## Description
Create database model to store mobile device tokens (FCM tokens) and API endpoints to register/unregister devices.

## Acceptance Criteria
- [ ] Create \`app/models/device_token.py\` model
- [ ] Create \`app/schemas/device.py\` (DeviceTokenCreate, DeviceTokenResponse)
- [ ] Add migration in \`main.py\` to create \`device_tokens\` table
- [ ] Create \`app/api/v1/routes/devices.py\`
  - \`POST /api/v1/devices/register\`
  - \`DELETE /api/v1/devices/unregister\`
  - \`GET /api/v1/devices/my-devices\`
- [ ] Mount devices router in \`app/api/v1/__init__.py\`
- [ ] Add validation (token length, platform enum)
- [ ] Handle duplicate tokens (reactivate if exists)
- [ ] Write tests for device endpoints
- [ ] Document in Swagger

## Dependencies
Requires API versioning and Firebase setup

## Estimated Effort
1-2 days"

gh issue create \
  --title "Implement Push Notification Service" \
  --label "backend,service,push-notifications,mobile-prep,priority:high" \
  --body "## Description
Create push notification service to send notifications via Firebase Cloud Messaging to registered devices.

## Acceptance Criteria
- [ ] Create \`app/services/push_notification_service.py\`
- [ ] Implement \`send_push_notification(db, user_id, title, body, data)\`
- [ ] Implement \`send_bulk_push_notification()\` for multiple users
- [ ] Support multicast (send to all user's devices)
- [ ] Handle failed tokens (deactivate invalid tokens)
- [ ] Add logging for successful/failed sends
- [ ] Graceful degradation if Firebase not configured
- [ ] Write unit tests
- [ ] Document usage

## Dependencies
Requires Firebase setup and DeviceToken model

## Estimated Effort
1-2 days"

gh issue create \
  --title "Integrate Push Notifications with Key Events" \
  --label "backend,api,push-notifications,enhancement,priority:high" \
  --body "## Description
Integrate push notification service with key user events: assignment creation, new messages, grade posting, etc.

## Acceptance Criteria
- [ ] New Assignment Created → Notify enrolled students
- [ ] New Message Received → Notify recipient
- [ ] Grade Posted → Notify student and parents
- [ ] Invitation Sent → Notify invitee
- [ ] Add deep links to all notifications
- [ ] Test each notification type
- [ ] Document notification triggers

## Dependencies
Requires push notification service

## Estimated Effort
2 days"

gh issue create \
  --title "Implement Assignment Reminder Background Job" \
  --label "backend,background-jobs,push-notifications,enhancement,priority:medium" \
  --body "## Description
Create scheduled background job to send daily reminders for assignments due the next day.

## Acceptance Criteria
- [ ] Create \`app/jobs/notification_jobs.py\`
- [ ] Implement \`send_assignment_reminders()\` function
- [ ] Schedule job to run daily at 6:00 PM
- [ ] Start scheduler in \`main.py\` startup event
- [ ] Add logging for job execution
- [ ] Test job execution
- [ ] Document job

## Dependencies
Requires push notification service

## Estimated Effort
1 day"

gh issue create \
  --title "Add Profile Picture Upload Endpoint" \
  --label "backend,api,file-upload,mobile-prep,priority:medium" \
  --body "## Description
Implement file upload endpoint for profile pictures with image resizing and cloud storage.

## Acceptance Criteria
- [ ] Install dependencies: \`python-multipart\`, \`Pillow\`, \`google-cloud-storage\`
- [ ] Create \`app/services/file_storage_service.py\`
- [ ] Create \`app/api/v1/routes/uploads.py\`
- [ ] Add \`profile_picture_url\` column to \`users\` table
- [ ] Add migration to \`main.py\`
- [ ] Update \`UserResponse\` schema
- [ ] Mount uploads router
- [ ] Set up GCS bucket
- [ ] Write tests
- [ ] Document in Swagger

## Dependencies
Requires API versioning

## Estimated Effort
2 days"

gh issue create \
  --title "Add Assignment File Upload Endpoint" \
  --label "backend,api,file-upload,mobile-prep,priority:medium" \
  --body "## Description
Implement file upload endpoint for assignment submissions (PDFs, images, documents).

## Acceptance Criteria
- [ ] Add \`POST /api/v1/uploads/assignment\` endpoint
- [ ] Accept file types: PDF, JPEG, PNG, DOC, DOCX
- [ ] Max file size: 10MB
- [ ] Upload to GCS bucket
- [ ] Store file metadata
- [ ] Link file to assignment and student
- [ ] Return file URL
- [ ] Write tests
- [ ] Document in Swagger

## Dependencies
Requires profile picture upload (reuses file storage service)

## Estimated Effort
1-2 days"

gh issue create \
  --title "Enhance Health Endpoint with Version Info" \
  --label "backend,api,enhancement,mobile-prep,priority:low" \
  --body "## Description
Enhance \`/health\` endpoint to include API version and feature flags for mobile force-update logic.

## Acceptance Criteria
- [ ] Add \`GET /api/v1/health\` endpoint
- [ ] Return status, version, min_supported_version, timestamp, features
- [ ] Document in Swagger

## Dependencies
Requires API versioning

## Estimated Effort
1 hour"

gh issue create \
  --title "Write Integration Tests for v1 API" \
  --label "backend,testing,mobile-prep,priority:medium" \
  --body "## Description
Write comprehensive integration tests for all v1 API endpoints to ensure mobile compatibility.

## Acceptance Criteria
- [ ] Create \`tests/api/v1/\` directory
- [ ] Test auth endpoints (login, refresh, logout)
- [ ] Test device endpoints (register, unregister)
- [ ] Test pagination on list endpoints
- [ ] Test error responses
- [ ] Test file uploads
- [ ] All tests pass
- [ ] Code coverage > 80% for v1 routes

## Dependencies
Requires all backend issues to be completed

## Estimated Effort
2-3 days"

echo ""
echo "Phase 1 (Backend) issues created! ✅"
echo ""
echo "Creating Phase 2: Mobile App issues..."

# Phase 2: Mobile App Development (18 issues)

gh issue create \
  --title "Initialize React Native Project with Expo" \
  --label "mobile,setup,react-native,priority:high" \
  --body "## Description
Set up React Native project using Expo for faster development and easier builds.

## Acceptance Criteria
- [ ] Install Expo CLI globally
- [ ] Create new Expo project with TypeScript template
- [ ] Install core dependencies
- [ ] Configure TypeScript
- [ ] Set up ESLint and Prettier
- [ ] Test app runs on iOS simulator
- [ ] Test app runs on Android emulator
- [ ] Test app runs on physical device (Expo Go)
- [ ] Document setup in \`mobile/README.md\`

## Dependencies
None

## Estimated Effort
1 day"

gh issue create \
  --title "Set Up Shared Code Folder" \
  --label "mobile,web,code-reuse,priority:high" \
  --body "## Description
Create shared code folder to maximize code reuse between web and mobile apps.

## Acceptance Criteria
- [ ] Create \`shared/\` folder at project root
- [ ] Set up directory structure (api, hooks, types, utils)
- [ ] Copy API client from web app
- [ ] Adapt for React Native (AsyncStorage instead of localStorage)
- [ ] Copy API endpoint files
- [ ] Update base URL to use \`/api/v1\`
- [ ] Configure TypeScript path aliases
- [ ] Test imports work in both web and mobile
- [ ] Document shared code structure

## Dependencies
Requires React Native project and API v1 endpoints

## Estimated Effort
2 days"

gh issue create \
  --title "Implement Authentication Flow (Login/Register)" \
  --label "mobile,auth,ui,priority:high" \
  --body "## Description
Implement login and register screens with JWT token storage and automatic token refresh.

## Acceptance Criteria
- [ ] Create AuthContext
- [ ] Create LoginScreen
- [ ] Create RegisterScreen
- [ ] Implement token storage in AsyncStorage
- [ ] Implement automatic token refresh on 401
- [ ] Create useAuth hook
- [ ] Set up React Navigation with auth flow
- [ ] Test login flow end-to-end
- [ ] Test register flow end-to-end
- [ ] Test token refresh
- [ ] Test logout

## Dependencies
Requires shared code setup

## Estimated Effort
2-3 days"

gh issue create \
  --title "Implement Dashboard Screen (Role-Based)" \
  --label "mobile,ui,dashboard,priority:high" \
  --body "## Description
Create role-based dashboard screen showing different content for students, parents, teachers, and admins.

## Acceptance Criteria
- [ ] Create DashboardScreen
- [ ] Display welcome message with user name
- [ ] Show role-specific content
- [ ] Add quick action buttons
- [ ] Fetch data using React Query
- [ ] Show loading skeleton
- [ ] Handle errors gracefully
- [ ] Pull-to-refresh functionality
- [ ] Test on iOS and Android

## Dependencies
Requires authentication flow

## Estimated Effort
2 days"

gh issue create \
  --title "Implement Courses Screen with Pagination" \
  --label "mobile,ui,courses,priority:high" \
  --body "## Description
Create courses list screen with infinite scroll pagination, search, and filtering.

## Acceptance Criteria
- [ ] Create CoursesScreen
- [ ] Create CourseCard component
- [ ] Implement infinite scroll pagination
- [ ] Add search bar
- [ ] Add filter buttons
- [ ] Pull-to-refresh
- [ ] Empty state
- [ ] Loading skeleton
- [ ] Error handling
- [ ] Navigate to course detail on tap
- [ ] Test on iOS and Android

## Dependencies
Requires dashboard screen and backend pagination

## Estimated Effort
2 days"

gh issue create \
  --title "Implement Course Detail Screen" \
  --label "mobile,ui,courses,priority:high" \
  --body "## Description
Create course detail screen showing course info, assignments, announcements, and students.

## Acceptance Criteria
- [ ] Create CourseDetailScreen
- [ ] Show course header
- [ ] Show tabs (Assignments, Announcements, Students, Content)
- [ ] Fetch course data and assignments
- [ ] Allow enrollment/unenrollment
- [ ] Navigate to assignment detail
- [ ] Pull-to-refresh
- [ ] Loading states
- [ ] Error handling
- [ ] Test on iOS and Android

## Dependencies
Requires courses screen

## Estimated Effort
2 days"

gh issue create \
  --title "Implement Assignments Screen" \
  --label "mobile,ui,assignments,priority:high" \
  --body "## Description
Create assignments list screen with filtering by status and sorting by due date.

## Acceptance Criteria
- [ ] Create AssignmentsScreen
- [ ] Create AssignmentCard component
- [ ] Show filter buttons (All, Pending, Submitted, Overdue)
- [ ] Sort by due date
- [ ] Group by course (optional)
- [ ] Pull-to-refresh
- [ ] Navigate to assignment detail
- [ ] Empty states
- [ ] Loading skeleton
- [ ] Test on iOS and Android

## Dependencies
Requires dashboard screen

## Estimated Effort
2 days"

gh issue create \
  --title "Implement Assignment Detail Screen" \
  --label "mobile,ui,assignments,priority:high" \
  --body "## Description
Create assignment detail screen showing assignment info, submission form, and grade.

## Acceptance Criteria
- [ ] Create AssignmentDetailScreen
- [ ] Show assignment details
- [ ] Show submission section (student view)
- [ ] Show grade section (if graded)
- [ ] Show submissions list (teacher view)
- [ ] Fetch assignment data
- [ ] Submit assignment
- [ ] Loading states
- [ ] Error handling
- [ ] Test on iOS and Android

## Dependencies
Requires assignments screen

## Estimated Effort
2-3 days"

gh issue create \
  --title "Implement Messages/Chat Screen" \
  --label "mobile,ui,messaging,priority:high" \
  --body "## Description
Create messaging screen with conversation list and chat interface.

## Acceptance Criteria
- [ ] Create MessagesScreen (conversation list)
- [ ] Create ChatScreen (individual conversation)
- [ ] Create MessageBubble component
- [ ] Fetch conversations and messages
- [ ] Send messages
- [ ] Pull-to-refresh
- [ ] Real-time updates (optional)
- [ ] Empty states
- [ ] Loading states
- [ ] Test on iOS and Android

## Dependencies
Requires dashboard screen

## Estimated Effort
3 days"

gh issue create \
  --title "Implement Notifications Screen" \
  --label "mobile,ui,notifications,priority:medium" \
  --body "## Description
Create notifications screen showing all user notifications with mark-as-read functionality.

## Acceptance Criteria
- [ ] Create NotificationsScreen
- [ ] Create NotificationCard component
- [ ] Fetch notifications with pagination
- [ ] Mark as read on tap
- [ ] \"Mark all as read\" button
- [ ] Filter: All, Unread
- [ ] Pull-to-refresh
- [ ] Navigate to related content
- [ ] Empty state
- [ ] Loading skeleton
- [ ] Test on iOS and Android

## Dependencies
Requires dashboard screen

## Estimated Effort
1-2 days"

gh issue create \
  --title "Implement User Profile & Settings Screen" \
  --label "mobile,ui,profile,priority:medium" \
  --body "## Description
Create user profile screen showing user info with edit capability and app settings.

## Acceptance Criteria
- [ ] Create ProfileScreen
- [ ] Show user info
- [ ] Edit profile section
- [ ] Settings section (notifications, dark mode)
- [ ] Account section (logout, delete account)
- [ ] Fetch and update user data
- [ ] Test on iOS and Android

## Dependencies
Requires dashboard screen

## Estimated Effort
2 days"

gh issue create \
  --title "Implement Camera & File Upload" \
  --label "mobile,file-upload,camera,priority:high" \
  --body "## Description
Implement camera and file picker for uploading profile pictures and assignment files.

## Acceptance Criteria
- [ ] Install expo-image-picker and expo-document-picker
- [ ] Create uploadService
- [ ] Create ImagePicker component
- [ ] Request camera/gallery permissions
- [ ] Handle permission denials
- [ ] Show upload progress
- [ ] Handle upload errors
- [ ] Compress images before upload
- [ ] Test on iOS and Android
- [ ] Test with different file types

## Dependencies
Requires backend file upload endpoints

## Estimated Effort
2 days"

gh issue create \
  --title "Set Up Firebase in Mobile App" \
  --label "mobile,push-notifications,firebase,priority:high" \
  --body "## Description
Configure Firebase Cloud Messaging in React Native app for push notifications.

## Acceptance Criteria
- [ ] Install Firebase packages
- [ ] Download and place Firebase config files
- [ ] Configure Android and iOS
- [ ] Create pushNotificationService
- [ ] Request permission on app startup
- [ ] Register device after login
- [ ] Unregister device on logout
- [ ] Test foreground notifications
- [ ] Test background notifications
- [ ] Test notification tap navigation
- [ ] Document setup

## Dependencies
Requires React Native project and backend Firebase setup

## Estimated Effort
2-3 days"

gh issue create \
  --title "Implement Deep Linking for Notifications" \
  --label "mobile,navigation,push-notifications,priority:medium" \
  --body "## Description
Implement deep linking to navigate to specific screens when user taps a push notification.

## Acceptance Criteria
- [ ] Configure deep link URL scheme
- [ ] Update app.json
- [ ] Create DeepLinkingConfig
- [ ] Map paths to screens
- [ ] Handle deep links from notifications
- [ ] Test each deep link type
- [ ] Handle invalid deep links
- [ ] Test on iOS and Android

## Dependencies
Requires Firebase in mobile app

## Estimated Effort
1-2 days"

gh issue create \
  --title "Implement Offline Mode with Data Caching" \
  --label "mobile,offline,caching,priority:medium,enhancement" \
  --body "## Description
Implement basic offline mode using React Query cache persistence and optimistic updates.

## Acceptance Criteria
- [ ] Install persist-client and MMKV
- [ ] Configure React Query cache persistence
- [ ] Set cache times
- [ ] Implement optimistic updates
- [ ] Show offline banner
- [ ] Show syncing indicator
- [ ] Queue mutations while offline
- [ ] Handle sync conflicts
- [ ] Test offline scenarios
- [ ] Document offline behavior

## Dependencies
Requires dashboard screen

## Estimated Effort
2-3 days"

gh issue create \
  --title "Implement Pull-to-Refresh on All Screens" \
  --label "mobile,ui,enhancement,priority:low" \
  --body "## Description
Add pull-to-refresh functionality to all list screens.

## Acceptance Criteria
- [ ] Add RefreshControl to all list screens
- [ ] Trigger React Query refetch on pull
- [ ] Show loading spinner
- [ ] Test on iOS and Android
- [ ] Ensure smooth animation

## Dependencies
Requires all screen issues

## Estimated Effort
1 day"

gh issue create \
  --title "Implement Loading Skeletons" \
  --label "mobile,ui,enhancement,priority:low" \
  --body "## Description
Add loading skeleton screens for better perceived performance.

## Acceptance Criteria
- [ ] Install react-native-skeleton-placeholder
- [ ] Create skeleton components
- [ ] Show skeletons while loading
- [ ] Match skeleton layout to actual cards
- [ ] Test on iOS and Android

## Dependencies
Requires all screen issues

## Estimated Effort
1 day"

gh issue create \
  --title "Write Mobile App Tests" \
  --label "mobile,testing,priority:medium" \
  --body "## Description
Write unit and integration tests for mobile app components and screens.

## Acceptance Criteria
- [ ] Install jest and testing-library
- [ ] Configure Jest for React Native
- [ ] Write component tests
- [ ] Write screen tests
- [ ] Write hook tests
- [ ] Write service tests
- [ ] Code coverage > 60%
- [ ] All tests pass
- [ ] Document testing

## Dependencies
Requires all mobile issues

## Estimated Effort
3 days"

echo ""
echo "Phase 2 (Mobile App) issues created! ✅"
echo ""
echo "Creating Phase 3: Testing & Deployment issues..."

# Phase 3: Testing & Deployment (6 issues)

gh issue create \
  --title "Manual Testing - iOS" \
  --label "mobile,testing,ios,priority:high" \
  --body "## Description
Comprehensive manual testing of all features on iOS devices.

## Acceptance Criteria
- [ ] Test all screens on iPhone SE (small screen)
- [ ] Test all screens on iPhone 14 Pro Max (large screen)
- [ ] Test Dark Mode
- [ ] Test landscape orientation
- [ ] Test offline mode
- [ ] Test push notifications
- [ ] Test deep links
- [ ] Test camera & photo upload
- [ ] Test file upload
- [ ] Test authentication flow
- [ ] Test logout
- [ ] Performance testing
- [ ] Memory leak testing
- [ ] Create bug tickets for issues

## Dependencies
Requires all mobile issues

## Estimated Effort
2 days"

gh issue create \
  --title "Manual Testing - Android" \
  --label "mobile,testing,android,priority:high" \
  --body "## Description
Comprehensive manual testing of all features on Android devices.

## Acceptance Criteria
- [ ] Test all screens on Pixel 5
- [ ] Test all screens on Samsung S21
- [ ] Test on Android tablet
- [ ] Test Dark Mode
- [ ] Test landscape orientation
- [ ] Test offline mode
- [ ] Test push notifications
- [ ] Test deep links
- [ ] Test camera & photo upload
- [ ] Test file upload
- [ ] Test authentication flow
- [ ] Test logout
- [ ] Test back button behavior
- [ ] Performance testing
- [ ] Create bug tickets for issues

## Dependencies
Requires all mobile issues

## Estimated Effort
2 days"

gh issue create \
  --title "Beta Testing with TestFlight (iOS)" \
  --label "mobile,testing,ios,beta,priority:high" \
  --body "## Description
Deploy beta version to TestFlight for internal/external testing.

## Acceptance Criteria
- [ ] Create Apple Developer account
- [ ] Create App Store Connect app record
- [ ] Configure app metadata
- [ ] Build iOS app for production
- [ ] Upload build to App Store Connect
- [ ] Create testing groups
- [ ] Invite beta testers
- [ ] Collect feedback
- [ ] Fix critical bugs
- [ ] Release updated builds

## Dependencies
Requires iOS manual testing

## Estimated Effort
1-2 days + ongoing feedback"

gh issue create \
  --title "Beta Testing with Google Play Internal Testing (Android)" \
  --label "mobile,testing,android,beta,priority:high" \
  --body "## Description
Deploy beta version to Google Play Internal Testing.

## Acceptance Criteria
- [ ] Create Google Play Console account
- [ ] Create app record
- [ ] Configure app metadata
- [ ] Build Android app for production
- [ ] Upload AAB to Play Console
- [ ] Create testing tracks
- [ ] Invite beta testers
- [ ] Collect feedback
- [ ] Fix critical bugs
- [ ] Release updated builds

## Dependencies
Requires Android manual testing

## Estimated Effort
1-2 days + ongoing feedback"

gh issue create \
  --title "Prepare App Store Submission - iOS" \
  --label "mobile,deployment,ios,app-store,priority:high" \
  --body "## Description
Prepare all assets and metadata for iOS App Store submission.

## Acceptance Criteria
- [ ] Create app icon (1024x1024)
- [ ] Create screenshots for all device sizes
- [ ] Write app description
- [ ] Write release notes
- [ ] Set app category (Education)
- [ ] Set content rating
- [ ] Set privacy policy URL
- [ ] Set support URL
- [ ] Submit for App Review
- [ ] Respond to feedback
- [ ] App approved ✅

## Dependencies
Requires TestFlight beta testing

## Estimated Effort
2-3 days + review time"

gh issue create \
  --title "Prepare Google Play Submission - Android" \
  --label "mobile,deployment,android,google-play,priority:high" \
  --body "## Description
Prepare all assets and metadata for Google Play Store submission.

## Acceptance Criteria
- [ ] Create app icon (512x512)
- [ ] Create feature graphic (1024x500)
- [ ] Create screenshots for all devices
- [ ] Write app description
- [ ] Write release notes
- [ ] Set app category (Education)
- [ ] Set content rating
- [ ] Set privacy policy URL
- [ ] Set data safety section
- [ ] Submit for review
- [ ] Respond to feedback
- [ ] App approved ✅

## Dependencies
Requires Play internal testing

## Estimated Effort
2-3 days + review time"

echo ""
echo "Phase 3 (Testing & Deployment) issues created! ✅"
echo ""
echo "Creating Documentation issues..."

# Documentation (3 issues)

gh issue create \
  --title "Write Mobile API Documentation" \
  --label "documentation,api,priority:medium" \
  --body "## Description
Create comprehensive API documentation for mobile developers.

## Acceptance Criteria
- [ ] Document all v1 endpoints in Swagger/OpenAPI
- [ ] Add request/response examples
- [ ] Document authentication flow
- [ ] Document pagination pattern
- [ ] Document error response format
- [ ] Document push notification payload
- [ ] Document deep link URL scheme
- [ ] Document file upload requirements
- [ ] Create Postman collection
- [ ] Host API docs (Swagger UI)
- [ ] Create Getting Started guide

## Dependencies
Requires all backend issues

## Estimated Effort
2 days"

gh issue create \
  --title "Write Mobile App README" \
  --label "documentation,mobile,priority:medium" \
  --body "## Description
Create comprehensive README for mobile app with setup instructions and architecture overview.

## Acceptance Criteria
- [ ] Document prerequisites
- [ ] Document installation steps
- [ ] Document how to run
- [ ] Document folder structure
- [ ] Document architecture
- [ ] Document shared code usage
- [ ] Document environment variables
- [ ] Document build process
- [ ] Document testing
- [ ] Document contribution guidelines
- [ ] Document known issues
- [ ] Add screenshots

## Dependencies
Requires all mobile issues

## Estimated Effort
1 day"

gh issue create \
  --title "Create Mobile Development Onboarding Guide" \
  --label "documentation,onboarding,priority:low" \
  --body "## Description
Create onboarding guide for new developers joining the mobile team.

## Acceptance Criteria
- [ ] Create ONBOARDING.md
- [ ] Document setup checklist
- [ ] Document codebase tour
- [ ] Document common tasks
- [ ] Document debugging tips
- [ ] Document common pitfalls
- [ ] Link to learning resources

## Dependencies
None

## Estimated Effort
1 day"

echo ""
echo "Documentation issues created! ✅"
echo ""
echo "Creating Risk Management issues..."

# Risk Management (3 issues)

gh issue create \
  --title "RISK: App Store Rejection (iOS)" \
  --label "risk,ios,app-store,priority:high" \
  --body "## Description
Track risk of Apple App Store rejection and prepare mitigations.

## Common Rejection Reasons
1. Privacy Policy Missing
2. In-App Purchases Not Using Apple IAP
3. Crashes on Launch
4. Incomplete Functionality
5. Design Guideline Violations

## Mitigation Plan
- [ ] Review Apple App Store Review Guidelines
- [ ] Ensure privacy policy is hosted and linked
- [ ] Test on all supported iOS versions (iOS 13+)
- [ ] Avoid restricted APIs
- [ ] Have review response template ready
- [ ] Plan for 1-2 week review time

## Related Issues
App Store Submission"

gh issue create \
  --title "RISK: Push Notification Delivery Failures" \
  --label "risk,push-notifications,priority:high" \
  --body "## Description
Track risk of push notifications failing to deliver and implement monitoring.

## Potential Issues
1. Invalid device tokens
2. Firebase quota exceeded
3. iOS permission denied
4. Android battery optimization

## Mitigation Plan
- [ ] Implement device token cleanup
- [ ] Monitor Firebase usage and costs
- [ ] Handle notification permission gracefully
- [ ] Add delivery logging
- [ ] Set up failure alerts
- [ ] Provide in-app fallback

## Related Issues
Push notification issues"

gh issue create \
  --title "RISK: File Upload Storage Costs" \
  --label "risk,infrastructure,costs,priority:medium" \
  --body "## Description
Track risk of excessive Google Cloud Storage costs from file uploads.

## Potential Issues
1. Users uploading very large files
2. Many file uploads
3. Storage never cleaned up

## Mitigation Plan
- [ ] Enforce file size limits (5MB profile, 10MB assignments)
- [ ] Compress images before upload
- [ ] Implement upload quota per user
- [ ] Add lifecycle policy to delete old files
- [ ] Monitor GCS usage monthly
- [ ] Set up billing alerts

## Related Issues
File upload issues"

echo ""
echo "All 42 issues created! 🎉"
echo ""
echo "Summary:"
echo "  - Backend API: 12 issues"
echo "  - Mobile App: 18 issues"
echo "  - Testing & Deployment: 6 issues"
echo "  - Documentation: 3 issues"
echo "  - Risk Management: 3 issues"
echo ""
echo "View all issues: gh issue list --label mobile-prep,mobile,testing,documentation,risk"
