import React, { useState } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import Svg, { Circle, Path, Rect } from "react-native-svg";
import { SafeAreaView } from "react-native-safe-area-context";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useNavigation } from "@react-navigation/native";
import type { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { api, Job } from "@/services/api";
import { JobStatusBadge } from "@/components/JobStatusBadge";
import { Button } from "@/components/Button";
import { GettingStarted } from "@/components/GettingStarted";
import { CharacterPortrait } from "@/components/CharacterPortrait";
import { authStore } from "@/store/authStore";
import { colors, spacing } from "@/theme";
import type { MainTabParams } from "@/navigation/types";

type Nav = BottomTabNavigationProp<MainTabParams>;

function TennisCourtArt() {
  return (
    <View pointerEvents="none" style={styles.courtArt}>
      <Svg width={140} height={130} viewBox="0 0 178 166" fill="none">
        <Rect
          x="27"
          y="10"
          width="122"
          height="146"
          rx="8"
          stroke={colors.primary}
          strokeWidth="2"
          opacity="0.42"
        />
        <Path
          d="M27 83h122M52 10v146M124 10v146M52 45h72v76H52z"
          stroke={colors.primary}
          strokeWidth="1.6"
          opacity="0.38"
        />
        <Circle cx="132" cy="37" r="17" fill="#E3B341" />
        <Path
          d="M122 24c11 9 15 22 13 34M141 22c-11 9-15 22-13 34"
          stroke="#FFF9E7"
          strokeWidth="2"
          opacity="0.9"
        />
      </Svg>
    </View>
  );
}

export default function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const [refreshing, setRefreshing] = useState(false);
  const userId = authStore((s) => s.user?.id);
  const query = useInfiniteQuery({
    queryKey: ["jobs", userId],
    initialPageParam: 1,
    queryFn: ({ pageParam }) => api.jobs.list(pageParam),
    getNextPageParam: (last) =>
      last.page * last.page_size < last.total ? last.page + 1 : undefined,
    refetchInterval: (current) =>
      current.state.data?.pages.some((page) =>
        page.jobs.some(
          (job) => job.status === "pending" || job.status === "processing",
        ),
      )
        ? 5000
        : false,
  });
  const jobs = query.data?.pages.flatMap((page) => page.jobs) ?? [];
  const hasJobs = jobs.length > 0;
  const total = query.data?.pages[0].total;
  const startAnalysis = () =>
    navigation.navigate("Record", { screen: "Sports" });
  const open = (job: Job) =>
    navigation.navigate("Record", {
      screen: job.status === "completed" ? "Result" : "UploadProgress",
      params: { jobId: job.id },
    });

  return (
    <SafeAreaView style={styles.page}>
      <FlatList
        data={jobs}
        keyExtractor={(job) => job.id}
        contentContainerStyle={styles.list}
        refreshing={refreshing}
        onRefresh={() => {
          setRefreshing(true);
          void query.refetch().finally(() => setRefreshing(false));
        }}
        onEndReached={() => {
          if (query.hasNextPage && !query.isFetching && !query.isError)
            void query.fetchNextPage();
        }}
        ListHeaderComponent={
          <View style={styles.headerContent}>
            <View style={styles.topBar}>
              <View style={styles.wordmark}>
                <View style={styles.wordmarkBall}>
                  <Text style={styles.wordmarkBallText}>S</Text>
                </View>
                <Text style={styles.wordmarkText} numberOfLines={1}>
                  Spolysis
                </Text>
              </View>
              <TouchableOpacity
                accessibilityRole="button"
                accessibilityLabel="Choose sport"
                onPress={() =>
                  navigation.navigate("Record", { screen: "Sports" })
                }
                style={styles.sportPill}
              >
                <Text style={styles.sportPillIcon}>🎾</Text>
                <Text style={styles.sportPillText} numberOfLines={1}>
                  Tennis
                </Text>
                <Text style={styles.sportPillChevron}>⌄</Text>
              </TouchableOpacity>
            </View>

            {hasJobs ? (
              <View style={styles.hero}>
                <TennisCourtArt />
                <View style={styles.heroCopy}>
                  <Text style={styles.eyebrow}>YOUR PRACTICE</Text>
                  <Text style={styles.heroTitle} maxFontSizeMultiplier={1.2}>
                    Make every swing count.
                  </Text>
                  <Text style={styles.heroDescription}>
                    See your movement clearly. Find one useful thing to work
                    on.
                  </Text>
                  <Button
                    title="Start an analysis"
                    onPress={startAnalysis}
                    style={styles.heroButton}
                  />
                </View>
              </View>
            ) : null}

            {hasJobs ? (
              <View style={styles.sectionHeading}>
                <View style={styles.sectionCopy}>
                  <Text style={styles.sectionTitle}>Recent analyses</Text>
                  <Text style={styles.sectionSubtitle}>
                    {total === undefined
                      ? "Your saved practice sessions"
                      : `${total} ${total === 1 ? "session" : "sessions"} saved`}
                  </Text>
                </View>
                {total ? (
                  <View style={styles.countPill}>
                    <Text style={styles.countText}>{total}</Text>
                  </View>
                ) : null}
              </View>
            ) : null}

            {query.isRefetchError && hasJobs ? (
              <View style={styles.notice}>
                <Text style={styles.noticeTitle} accessibilityRole="alert">
                  Could not refresh your analyses
                </Text>
                <Text style={styles.noticeText}>
                  Your saved sessions are still here. Check your connection and
                  try again.
                </Text>
                <Button
                  title="Try again"
                  variant="secondary"
                  loading={query.isRefetching}
                  onPress={() => void query.refetch()}
                />
              </View>
            ) : null}
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyCard}>
            {query.isLoading ? (
              <ActivityIndicator color={colors.primary} />
            ) : (
              <>
                {query.isError ? (
                  <View style={styles.emptyMark}>
                    <Text style={styles.emptyMarkText}>!</Text>
                  </View>
                ) : (
                  <CharacterPortrait character="pipkin" size={112} />
                )}
                <Text style={styles.emptyTitle} maxFontSizeMultiplier={1.2}>
                  {query.isError
                    ? "Your sessions could not load"
                    : "Your first session starts here"}
                </Text>
                <Text style={styles.emptyDescription}>
                  {query.isError
                    ? "Check your connection, then refresh your analyses."
                    : "Choose a stroke, record or import a clip, and explore your movement in 3D."}
                </Text>
                <Button
                  title={query.isError ? "Retry" : "Choose a sport"}
                  loading={query.isError && query.isFetching}
                  style={styles.emptyButton}
                  onPress={() => {
                    if (query.isError) void query.refetch();
                    else startAnalysis();
                  }}
                />
                {!query.isError ? <GettingStarted embedded /> : null}
              </>
            )}
          </View>
        }
        ListFooterComponent={
          query.isFetchNextPageError ? (
            <View style={styles.notice}>
              <Text style={styles.noticeTitle} accessibilityRole="alert">
                Could not load older analyses
              </Text>
              <Text style={styles.noticeText}>
                Your loaded sessions are still here. Check your connection and
                retry.
              </Text>
              <Button
                title="Retry loading"
                variant="secondary"
                loading={query.isFetchingNextPage}
                onPress={() => void query.fetchNextPage()}
              />
            </View>
          ) : query.isFetchingNextPage ? (
            <ActivityIndicator color={colors.primary} />
          ) : hasJobs ? (
            <TouchableOpacity
              accessibilityRole="button"
              onPress={startAnalysis}
              style={styles.moreButton}
            >
              <Text style={styles.moreButtonText}>Analyze another session</Text>
            </TouchableOpacity>
          ) : null
        }
        renderItem={({ item, index }) => (
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel={`Open analysis from ${new Date(item.created_at).toLocaleDateString()}`}
            onPress={() => open(item)}
            activeOpacity={0.78}
            style={styles.sessionCard}
          >
            <View
              style={[
                styles.sessionIcon,
                {
                  backgroundColor: PLAYER_COLORS[index % PLAYER_COLORS.length],
                },
              ]}
            >
              <Text style={styles.sessionIconText}>🎾</Text>
            </View>
            <View style={styles.sessionBody}>
              <Text style={styles.sessionTitle}>Tennis practice</Text>
              <Text style={styles.sessionDate}>
                {new Date(item.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </Text>
            </View>
            <View style={styles.sessionMeta}>
              <JobStatusBadge status={item.status} />
              <Text style={styles.sessionChevron}>›</Text>
            </View>
          </TouchableOpacity>
        )}
      />
    </SafeAreaView>
  );
}

const PLAYER_COLORS = [
  colors.peach,
  colors.teal,
  colors.mustard,
  colors.sage,
  colors.coral,
  colors.sky,
];

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  list: {
    flexGrow: 1,
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.xl,
    gap: spacing.sm,
  },
  headerContent: { gap: spacing.lg, paddingBottom: spacing.xs },
  topBar: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.xs,
  },
  wordmark: {
    minWidth: 0,
    flexShrink: 1,
    height: 40,
    paddingHorizontal: 12,
    borderRadius: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.surface,
  },
  wordmarkBall: {
    flexShrink: 0,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.mustard,
    alignItems: "center",
    justifyContent: "center",
  },
  wordmarkBallText: {
    color: colors.text.primary,
    fontFamily: "Fraunces_600SemiBold",
    fontSize: 14,
  },
  wordmarkText: {
    flexShrink: 1,
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 18,
  },
  sportPill: {
    minWidth: 0,
    flexShrink: 1,
    height: 40,
    paddingHorizontal: 13,
    borderRadius: 999,
    backgroundColor: colors.surface,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    shadowColor: "#281950",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
    elevation: 2,
  },
  sportPillIcon: { flexShrink: 0, fontSize: 15 },
  sportPillText: {
    flexShrink: 1,
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 16,
  },
  sportPillChevron: { color: colors.text.muted, fontSize: 16, marginLeft: 2 },
  hero: {
    minHeight: 270,
    padding: spacing.lg,
    borderRadius: 28,
    backgroundColor: colors.primaryMuted,
    overflow: "hidden",
    justifyContent: "center",
  },
  heroCopy: { maxWidth: "68%", gap: spacing.sm },
  eyebrow: {
    color: colors.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 11,
    letterSpacing: 1.1,
  },
  heroTitle: {
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 34,
    lineHeight: 39,
    letterSpacing: -0.8,
  },
  heroDescription: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    fontSize: 14,
    lineHeight: 20,
  },
  heroButton: { alignSelf: "stretch", marginTop: spacing.xs },
  courtArt: { position: "absolute", right: -16, top: 12, opacity: 0.7 },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 4,
    gap: spacing.sm,
  },
  sectionCopy: { flex: 1, flexShrink: 1, minWidth: 0 },
  sectionTitle: {
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 25,
  },
  sectionSubtitle: {
    marginTop: 2,
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    fontSize: 12,
  },
  countPill: {
    flexShrink: 0,
    minWidth: 34,
    height: 34,
    paddingHorizontal: 9,
    borderRadius: 17,
    backgroundColor: colors.surfaceElevated,
    alignItems: "center",
    justifyContent: "center",
  },
  countText: {
    color: colors.text.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 13,
  },
  sessionCard: {
    minHeight: 80,
    padding: spacing.sm,
    paddingRight: 13,
    borderRadius: 22,
    backgroundColor: colors.surface,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    shadowColor: "#281950",
    shadowOpacity: 0.035,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 1,
  },
  sessionIcon: {
    width: 52,
    height: 52,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  sessionIconText: { fontSize: 25 },
  sessionBody: { flex: 1, gap: 4 },
  sessionTitle: {
    color: colors.text.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 15,
  },
  sessionDate: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    fontSize: 12,
  },
  sessionMeta: { alignItems: "flex-end", gap: 2 },
  sessionChevron: { color: colors.text.muted, fontSize: 20, lineHeight: 20 },
  emptyCard: {
    flexGrow: 1,
    backgroundColor: colors.surface,
    borderRadius: 28,
    padding: spacing.lg,
    gap: spacing.md,
    alignItems: "flex-start",
  },
  emptyButton: { alignSelf: "stretch" },
  emptyMark: {
    width: 48,
    height: 48,
    borderRadius: 17,
    backgroundColor: colors.primaryMuted,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyMarkText: { color: colors.primary, fontSize: 26 },
  emptyTitle: {
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 25,
  },
  emptyDescription: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    fontSize: 14,
    lineHeight: 21,
  },
  notice: {
    backgroundColor: colors.surface,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    gap: spacing.sm,
  },
  noticeTitle: {
    color: colors.warning,
    fontFamily: "DMSans_700Bold",
    fontSize: 15,
  },
  noticeText: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    fontSize: 13,
    lineHeight: 19,
  },
  moreButton: { alignItems: "center", padding: spacing.md },
  moreButtonText: {
    color: colors.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 14,
  },
});
