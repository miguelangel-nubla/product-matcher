import {
  Alert,
  Box,
  Card,
  Container,
  createListCollection,
  Grid,
  Heading,
  HStack,
  SelectContent,
  SelectItem,
  SelectRoot,
  SelectTrigger,
  SelectValueText,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import useAuth from "@/hooks/useAuth"
import { MatchingService } from "../../client"

interface StatisticsData {
  total_products: number
  successful_matches: number
  pending_queries: number
  resolved_queries: number
  ignored_queries: number
}

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const [selectedBackend, setSelectedBackend] = useState("mock")

  // Load available backends
  const { data: backends, isLoading: isLoadingBackends } = useQuery({
    queryKey: ["backends"],
    queryFn: () => MatchingService.getAvailableBackends(),
  })

  // Create collection for backend select
  const backendCollection = createListCollection({
    items:
      (backends as any[])?.map((backend: any) => ({
        label: backend.description || backend.name,
        value: backend.name,
      })) || [],
  })

  const {
    data: stats,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["matching-stats", selectedBackend],
    queryFn: async () => {
      const response = await MatchingService.getMatchingStats({
        backend: selectedBackend,
      })
      return response as StatisticsData
    },
  })

  const matchRate =
    stats && stats.successful_matches + stats.resolved_queries > 0
      ? (
          (stats.successful_matches /
            (stats.successful_matches +
              stats.pending_queries +
              stats.resolved_queries)) *
          100
        ).toFixed(1)
      : "0"

  return (
    <Container maxW="container.xl" py={8}>
      <VStack gap={6} align="stretch">
        <Box>
          <Text fontSize="2xl" mb={2}>
            Hi, {currentUser?.full_name || currentUser?.email} 👋🏼
          </Text>
          <Text color="gray.600" mb={4}>
            Welcome back! Here's an overview of your product matching activity.
          </Text>
        </Box>

        <Card.Root>
          <Card.Header>
            <HStack justify="space-between" align="start">
              <Heading size="md">System Overview</Heading>
              <HStack align="center" gap={2}>
                <Text fontSize="sm">Backend:</Text>
                {isLoadingBackends ? (
                  <Spinner size="sm" />
                ) : (
                  <SelectRoot
                    collection={backendCollection}
                    value={[selectedBackend]}
                    onValueChange={(e) => setSelectedBackend(e.value[0])}
                    size="sm"
                    width="32"
                  >
                    <SelectTrigger>
                      <SelectValueText placeholder="Select backend" />
                    </SelectTrigger>
                    <SelectContent>
                      {backendCollection.items.map((item: any) => (
                        <SelectItem key={item.value} item={item.value}>
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </SelectRoot>
                )}
              </HStack>
            </HStack>
          </Card.Header>

          <Card.Body>
            {isLoading ? (
              <HStack justify="center" py={8}>
                <Spinner />
                <Text>Loading statistics...</Text>
              </HStack>
            ) : error ? (
              <Alert.Root status="error">
                <Alert.Indicator />
                <Alert.Description>
                  Failed to load statistics. Please try again.
                </Alert.Description>
              </Alert.Root>
            ) : (
              <Grid
                templateColumns={{
                  base: "1fr",
                  md: "repeat(2, 1fr)",
                  lg: "repeat(3, 1fr)",
                }}
                gap={6}
              >
                <Card.Root>
                  <Card.Body>
                    <VStack align="start" gap={2}>
                      <Text fontSize="sm" color="gray.600">
                        Total Products
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold">
                        {stats?.total_products || 0}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        Available in external system
                      </Text>
                    </VStack>
                  </Card.Body>
                </Card.Root>

                <Card.Root>
                  <Card.Body>
                    <VStack align="start" gap={2}>
                      <Text fontSize="sm" color="gray.600">
                        Successful Matches
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold" color="green.500">
                        {stats?.successful_matches || 0}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        Products matched automatically
                      </Text>
                    </VStack>
                  </Card.Body>
                </Card.Root>

                <Card.Root>
                  <Card.Body>
                    <VStack align="start" gap={2}>
                      <Text fontSize="sm" color="gray.600">
                        Pending Queries
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold" color="orange.500">
                        {stats?.pending_queries || 0}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        Awaiting manual resolution
                      </Text>
                    </VStack>
                  </Card.Body>
                </Card.Root>

                <Card.Root>
                  <Card.Body>
                    <VStack align="start" gap={2}>
                      <Text fontSize="sm" color="gray.600">
                        Resolved Queries
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold" color="blue.500">
                        {stats?.resolved_queries || 0}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        Manually resolved matches
                      </Text>
                    </VStack>
                  </Card.Body>
                </Card.Root>

                <Card.Root>
                  <Card.Body>
                    <VStack align="start" gap={2}>
                      <Text fontSize="sm" color="gray.600">
                        Ignored Queries
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold" color="gray.500">
                        {stats?.ignored_queries || 0}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        Queries marked as ignored
                      </Text>
                    </VStack>
                  </Card.Body>
                </Card.Root>

                <Card.Root>
                  <Card.Body>
                    <VStack align="start" gap={2}>
                      <Text fontSize="sm" color="gray.600">
                        Match Rate
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold" color="teal.500">
                        {matchRate}%
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        Automatic match success rate
                      </Text>
                    </VStack>
                  </Card.Body>
                </Card.Root>
              </Grid>
            )}
          </Card.Body>
        </Card.Root>
      </VStack>
    </Container>
  )
}
