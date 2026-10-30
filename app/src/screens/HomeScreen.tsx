import React, { useState } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useNavigation } from "@react-navigation/native";
import type { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { api, Job } from "@/services/api";
import { JobStatusBadge } from "@/components/JobStatusBadge";
import { Button } from "@/components/Button";
import { GettingStarted } from "@/components/GettingStarted";
import { authStore } from "@/store/authStore";
import { colors } from "@/theme";
import type { MainTabParams } from "@/navigation/types";

type Nav = BottomTabNavigationProp<MainTabParams>;
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
    refetchInterval: (query) =>
      query.state.data?.pages.some((p) =>
        p.jobs.some((j) => j.status === "pending" || j.status === "processing"),
      )
        ? 5000
        : false,
  });
  const jobs = query.data?.pages.flatMap((p) => p.jobs) ?? [];
  const open = (job: Job) =>
    navigation.navigate("Record", {
      screen: job.status === "completed" ? "Result" : "UploadProgress",
      params: { jobId: job.id },
    });
  return (
    <SafeAreaView style={styles.page}>
      <View style={styles.header}>
        <Text style={styles.title}>Your analyses</Text>
        <Text style={styles.muted}>
          {query.data
            ? `${query.data.pages[0].total} total`
            : query.isLoading
              ? "Loading..."
              : "Total unavailable"}
        </Text>
      </View>
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
          query.isRefetchError && jobs.length > 0 ? (
            <View style={styles.notice}>
              <Text style={styles.noticeTitle} accessibilityRole="alert">
                Could not update analyses
              </Text>
              <Text style={styles.description}>
                Showing previously loaded analyses. Their status may be out of
                date. Check your connection and retry.
              </Text>
              <Button
                title="Retry updating analyses"
                variant="secondary"
                loading={query.isRefetching}
                onPress={() => void query.refetch()}
              />
            </View>
          ) : null
        }
        ListFooterComponent={
          query.isFetchNextPageError ? (
            <View style={styles.notice}>
              <Text style={styles.noticeTitle} accessibilityRole="alert">
                Could not load more analyses
              </Text>
              <Text style={styles.description}>
                Your loaded analyses are still here. Check your connection and
                retry to see older recordings.
              </Text>
              <Button
                title="Retry loading more"
                variant="secondary"
                loading={query.isFetchingNextPage}
                onPress={() => void query.fetchNextPage()}
              />
            </View>
          ) : query.isFetchingNextPage ? (
            <ActivityIndicator color={colors.primary} />
          ) : null
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            {query.isLoading ? (
              <ActivityIndicator color={colors.primary} />
            ) : (
              <>
                <Text style={styles.emptyTitle}>
                  {query.isError ? "Could not load analyses" : "Get started"}
                </Text>
                <Text style={styles.description}>
                  {query.isError
                    ? "Check your connection, then try again."
                    : "Record or upload a tennis stroke to explore your movement in 3D."}
                </Text>
                {!query.isError && <GettingStarted />}
                <Button
                  title={query.isError ? "Retry" : "Start your first analysis"}
                  loading={query.isError && query.isFetching}
                  onPress={() => {
                    if (query.isError) void query.refetch();
                    else navigation.navigate("Record", { screen: "Capture" });
                  }}
                />
              </>
            )}
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel={`Open analysis from ${new Date(item.created_at).toLocaleDateString()}`}
            onPress={() => open(item)}
            style={styles.row}
          >
            <View style={styles.badge}>
              <Text style={styles.badgeText}>3D</Text>
            </View>
            <View style={styles.rowBody}>
              <Text style={styles.rowTitle}>
                {item.tier === "free" ? "Earlier analysis" : "Stroke analysis"}
              </Text>
              <Text style={styles.muted}>
                {new Date(item.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </Text>
            </View>
            <JobStatusBadge status={item.status} />
          </TouchableOpacity>
        )}
      />
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  header: {
    padding: 24,
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
  },
  title: { color: colors.text.primary, fontSize: 28, fontWeight: "700" },
  muted: { color: colors.text.muted, fontSize: 12 },
  list: { paddingHorizontal: 24, paddingBottom: 24, gap: 12, flexGrow: 1 },
  empty: { flex: 1, justifyContent: "center", gap: 20, paddingBottom: 60 },
  emptyTitle: { fontSize: 26, fontWeight: "600", color: colors.text.primary },
  description: { fontSize: 16, lineHeight: 24, color: colors.text.secondary },
  notice: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
    gap: 12,
    marginBottom: 12,
  },
  noticeTitle: { color: colors.warning, fontSize: 17, fontWeight: "600" },
  row: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  rowBody: { flex: 1, gap: 5 },
  rowTitle: { color: colors.text.primary, fontSize: 15, fontWeight: "600" },
  badge: {
    width: 40,
    height: 40,
    backgroundColor: colors.primaryMuted,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  badgeText: { color: colors.primary, fontWeight: "700" },
});
