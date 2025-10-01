import {
  Badge,
  Box,
  Button,
  Card,
  Code,
  Container,
  Heading,
  HStack,
  IconButton,
  Spinner,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { FiChevronLeft, FiChevronRight, FiChevronsLeft, FiChevronsRight } from "react-icons/fi"
import useAuth from "@/hooks/useAuth"
import { MatchingService } from "../../client"
import { ProductIdBadge } from "../../components/ProductIdBadge"

export const Route = createFileRoute("/_layout/logs")({
  component: MatchLogs,
})

function MatchLogs() {
  const { user: currentUser } = useAuth()
  const navigate = useNavigate()
  const [page, setPage] = useState(0)
  const limit = 10

  const { data: logs, isLoading } = useQuery({
    queryKey: ["match-logs", page],
    queryFn: () => MatchingService.getMatchLogs({ skip: page * limit, limit }),
  })

  const formatScore = (score: number) => {
    return (score * 100).toFixed(0)
  }

  const getScoreColor = (score: number, threshold: number) => {
    if (score >= threshold) return "green"
    if (score >= threshold * 0.8) return "yellow"
    return "red"
  }

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString() + " " + date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    } catch {
      // Fallback for invalid dates
      return dateStr.slice(0, 8) + "..."
    }
  }

  const handleOriginalTextClick = (log: any) => {
    navigate({
      to: "/matcher",
      search: {
        text: log.original_text,
        backend: log.backend,
        threshold: log.threshold_used,
      },
    })
  }

  const handlePreviousPage = () => {
    if (page > 0) {
      setPage(page - 1)
    }
  }

  const handleNextPage = () => {
    if (logs && (page + 1) * limit < logs.count) {
      setPage(page + 1)
    }
  }

  const totalPages = logs ? Math.ceil(logs.count / limit) : 0
  const hasNextPage = logs ? (page + 1) * limit < logs.count : false
  const hasPreviousPage = page > 0

  if (isLoading) {
    return (
      <Container maxW="full" centerContent>
        <Spinner size="xl" />
      </Container>
    )
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack gap={6} align="stretch">
        <Box>
          <Heading size="lg" mb={4}>
            Match History
          </Heading>
          <Text color="fg.muted">
            View your successful product matches and their details.
          </Text>
        </Box>

        <Card.Root>
          <Card.Header>
            <HStack justify="space-between">
              <Heading size="md">Matches</Heading>
              {logs?.data && logs.data.length > 0 && (
                <Text fontSize="sm" color="fg.muted">
                  Page {page + 1} of {totalPages}
                </Text>
              )}
            </HStack>
          </Card.Header>

          <Card.Body>
            {isLoading ? (
              <HStack justify="center" py={8}>
                <Spinner />
                <Text>Loading match history...</Text>
              </HStack>
            ) : !logs?.data?.length ? (
              <Text textAlign="center" color="fg.muted" py={8}>
                No match history found. Start matching products to see your history here!
              </Text>
            ) : (
              <Box overflowX="auto">
                <Table.Root size="sm" variant="outline">
                  <Table.Header>
                    <Table.Row>
                      <Table.ColumnHeader>Original Text</Table.ColumnHeader>
                      <Table.ColumnHeader>Normalized</Table.ColumnHeader>
                      <Table.ColumnHeader>Matched Product</Table.ColumnHeader>
                      <Table.ColumnHeader>Score</Table.ColumnHeader>
                      <Table.ColumnHeader>Backend</Table.ColumnHeader>
                      <Table.ColumnHeader>Date</Table.ColumnHeader>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {logs.data.map((log) => (
                      <Table.Row key={log.id}>
                        <Table.Cell>
                          <Button
                            variant="subtle"
                            size="xs"
                            px={2}
                            py={1}
                            onClick={() => handleOriginalTextClick(log)}
                          >
                            {log.original_text}
                          </Button>
                        </Table.Cell>
                        <Table.Cell>
                          <Code fontSize="sm" variant="surface">
                            {log.normalized_text}
                          </Code>
                        </Table.Cell>
                        <Table.Cell>
                          <VStack align="start" gap={1}>
                            <ProductIdBadge
                              productId={log.matched_product_id}
                              backend={log.backend}
                              size="sm"
                            />
                            <Text fontSize="xs" color="gray.500">
                              {log.matched_text}
                            </Text>
                          </VStack>
                        </Table.Cell>
                        <Table.Cell>
                          <HStack gap={1}>
                            <Badge
                              colorPalette={getScoreColor(
                                log.confidence_score,
                                log.threshold_used
                              )}
                            >
                              {formatScore(log.confidence_score)}
                            </Badge>
                            <Text fontSize="xs" color="gray.500">
                               / {formatScore(log.threshold_used)}
                            </Text>
                          </HStack>
                        </Table.Cell>
                        <Table.Cell>
                          <Badge variant="outline">{log.backend}</Badge>
                        </Table.Cell>
                        <Table.Cell>
                          <Text fontSize="sm" color="gray.600">
                            {formatDate(log.created_at)}
                          </Text>
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table.Root>
              </Box>
            )}

            {/* Pagination Controls */}
            {logs?.data?.length && totalPages > 1 ? (
              <Box pt={4} borderTop="1px solid" borderColor="border.muted">
                <HStack justify="space-between" align="center">
                  <Text fontSize="sm" color="fg.muted">
                    Showing {page * limit + 1}-{Math.min((page + 1) * limit, logs.count)} of {logs.count} matches
                  </Text>
                  <HStack gap={2}>
                    <IconButton
                      size="sm"
                      variant="outline"
                      disabled={page === 0}
                      onClick={() => setPage(0)}
                      aria-label="First page"
                    >
                      <FiChevronsLeft />
                    </IconButton>
                    <IconButton
                      size="sm"
                      variant="outline"
                      disabled={!hasPreviousPage}
                      onClick={handlePreviousPage}
                      aria-label="Previous page"
                    >
                      <FiChevronLeft />
                    </IconButton>
                    <Text fontSize="sm" color="fg.muted">
                      Page {page + 1} of {totalPages}
                    </Text>
                    <IconButton
                      size="sm"
                      variant="outline"
                      disabled={!hasNextPage}
                      onClick={handleNextPage}
                      aria-label="Next page"
                    >
                      <FiChevronRight />
                    </IconButton>
                    <IconButton
                      size="sm"
                      variant="outline"
                      disabled={!hasNextPage}
                      onClick={() => setPage(totalPages - 1)}
                      aria-label="Last page"
                    >
                      <FiChevronsRight />
                    </IconButton>
                  </HStack>
                </HStack>
              </Box>
            ) : null}
          </Card.Body>
        </Card.Root>
      </VStack>
    </Container>
  )
}