import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  CloseButton,
  Code,
  Container,
  createListCollection,
  Dialog,
  Heading,
  HStack,
  IconButton,
  Input,
  Portal,
  SelectContent,
  SelectItem,
  SelectRoot,
  SelectTrigger,
  SelectValueText,
  Spinner,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { useCallback, useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import {
  FiChevronLeft,
  FiChevronRight,
  FiChevronsLeft,
  FiChevronsRight,
} from "react-icons/fi"
import type { PendingQueryPublic, ResolveRequest } from "../../client"
import { MatchingService } from "../../client"
import { getErrorMessage } from "../../utils/error"

// Type for external products from adapters
interface ExternalProduct {
  id: string
  aliases: string[]
  description?: string
  category?: string
  barcode?: string
}

import { ProductCard } from "../../components/ProductCard"
import { ProductIdBadge } from "../../components/ProductIdBadge"
import { QueryCard } from "../../components/QueryCard"
import { Field } from "../../components/ui/field"

interface ResolveForm {
  action: "assign" | "ignore"
  product_id?: string
  custom_alias?: string
}

// Create collections for select options
const statusCollection = createListCollection({
  items: [
    { label: "Pending", value: "pending" },
    { label: "Resolved", value: "resolved" },
    { label: "Ignored", value: "ignored" },
  ],
})

const actionCollection = createListCollection({
  items: [
    { label: "Add alias to existing product", value: "assign" },
    { label: "Ignore (mark as resolved)", value: "ignore" },
  ],
})

function PendingItems() {
  const navigate = useNavigate()
  const { queryId } = useSearch({ from: "/_layout/pending" })
  const [selectedStatus, setSelectedStatus] = useState("pending")
  const [selectedQuery, setSelectedQuery] = useState<PendingQueryPublic | null>(
    null,
  )
  const [isOpen, setIsOpen] = useState(false)
  const [productSearch, setProductSearch] = useState("")
  const [selectedProduct, setSelectedProduct] =
    useState<ExternalProduct | null>(null)
  const [currentPage, setCurrentPage] = useState(0)
  const itemsPerPage = 20
  const [deletingItemId, setDeletingItemId] = useState<string | null>(null)

  const queryClient = useQueryClient()

  const { register, handleSubmit, watch, reset, setValue } =
    useForm<ResolveForm>({
      defaultValues: {
        action: "assign",
      },
    })

  const action = watch("action")

  const { data: pendingQueries, isLoading } = useQuery({
    queryKey: ["pending-queries", selectedStatus, currentPage],
    queryFn: () =>
      MatchingService.getPendingQueries({
        status: selectedStatus,
        limit: itemsPerPage,
        skip: currentPage * itemsPerPage,
      }),
  })

  const { data: settings } = useQuery({
    queryKey: ["matching-settings"],
    queryFn: () => MatchingService.getMatchingSettings(),
  })

  const handleResolveClick = useCallback(
    (item: PendingQueryPublic) => {
      setSelectedQuery(item)
      setSelectedProduct(null)
      setProductSearch("")
      reset({
        action: "assign",
        custom_alias: item.normalized_text, // Use the current item's normalized text
      })
      setIsOpen(true)
    },
    [reset],
  )

  // Auto-open resolve dialog if queryId is provided in URL
  useEffect(() => {
    if (queryId && pendingQueries?.data && !isLoading) {
      const targetQuery = pendingQueries.data.find((q) => q.id === queryId)
      if (targetQuery) {
        handleResolveClick(targetQuery) // Reuse existing logic
      }
    }
  }, [queryId, pendingQueries?.data, isLoading, handleResolveClick])

  // Reset page when status changes
  useEffect(() => {
    setCurrentPage(0)
  }, [])

  // Get external products based on the selected item's backend
  const { data: products, isLoading: isLoadingProducts } = useQuery({
    queryKey: ["external-products", selectedQuery?.backend],
    queryFn: async () => {
      if (!selectedQuery?.backend) return { data: [], count: 0, backend: "" }

      const result = await MatchingService.getExternalProducts({
        backend: selectedQuery.backend,
      })
      return result
    },
    enabled: !!selectedQuery?.backend,
  })

  const resolveMutation = useMutation({
    mutationFn: (data: ResolveRequest) =>
      MatchingService.resolvePendingQuery({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending-queries"] })
      setIsOpen(false)
      reset()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (pendingQueryId: string) => {
      setDeletingItemId(pendingQueryId)
      return MatchingService.deletePendingQuery({ pendingQueryId })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending-queries"] })
      setDeletingItemId(null)
    },
    onError: () => {
      setDeletingItemId(null)
    },
  })

  const filteredProducts =
    (products as any)?.data?.filter(
      (product: ExternalProduct) =>
        product.aliases?.[0]
          ?.toLowerCase()
          .includes(productSearch.toLowerCase()) ||
        product.id.toLowerCase().includes(productSearch.toLowerCase()) ||
        product.aliases?.some((alias: string) =>
          alias.toLowerCase().includes(productSearch.toLowerCase()),
        ),
    ) || []

  const onSubmit = useCallback(
    (data: ResolveForm) => {
      if (!selectedQuery) return
      if (data.action === "assign" && !selectedProduct) {
        return
      }

      const resolveRequest: ResolveRequest = {
        pending_query_id: selectedQuery.id,
        action: data.action,
        ...(data.action === "assign" &&
          selectedProduct && { product_id: selectedProduct.id }),
        ...(data.custom_alias && { custom_alias: data.custom_alias }),
      }

      resolveMutation.mutate(resolveRequest, {
        onSuccess: () => {
          setIsOpen(false)
          setSelectedProduct(null)
          setProductSearch("")
          reset()
        },
      })
    },
    [selectedQuery, selectedProduct, resolveMutation, reset],
  )

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!isOpen) return

      if (event.key === "Escape") {
        setIsOpen(false)
      } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault()
        if (action === "assign" && selectedProduct) {
          handleSubmit(onSubmit)()
        } else if (action === "ignore") {
          handleSubmit(onSubmit)()
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, action, selectedProduct, handleSubmit, onSubmit])

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "orange"
      case "resolved":
        return "green"
      case "ignored":
        return "gray"
      default:
        return "gray"
    }
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack gap={6} align="stretch">
        <Box>
          <Heading size="lg" mb={4}>
            Unmatched Queries
          </Heading>
          <Text color="fg.muted">
            Manage product matches that need manual resolution.
          </Text>
        </Box>

        <Card.Root>
          <Card.Header>
            <HStack justify="space-between">
              <Heading size="md">Queries</Heading>
              <HStack>
                <Text fontSize="sm">Status:</Text>
                <SelectRoot
                  collection={statusCollection}
                  value={[selectedStatus]}
                  onValueChange={(e) => setSelectedStatus(e.value[0])}
                  size="sm"
                  width="32"
                >
                  <SelectTrigger>
                    <SelectValueText placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {statusCollection.items.map((item) => (
                      <SelectItem key={item.value} item={item}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </SelectRoot>
              </HStack>
            </HStack>
          </Card.Header>

          <Card.Body>
            {isLoading ? (
              <HStack justify="center" py={8}>
                <Spinner />
                <Text>Loading unmatched queries...</Text>
              </HStack>
            ) : !pendingQueries?.data?.length ? (
              <Alert.Root status="info">
                <Alert.Indicator />
                <Alert.Description>
                  No {selectedStatus} queries found.
                </Alert.Description>
              </Alert.Root>
            ) : (
              <Box overflowX="auto">
                <Table.Root size="sm" variant="outline">
                  <Table.Header>
                    <Table.Row>
                      <Table.ColumnHeader>Original Text</Table.ColumnHeader>
                      <Table.ColumnHeader>Normalized Text</Table.ColumnHeader>
                      <Table.ColumnHeader>Backend</Table.ColumnHeader>
                      <Table.ColumnHeader>Candidates</Table.ColumnHeader>
                      <Table.ColumnHeader>Status</Table.ColumnHeader>
                      <Table.ColumnHeader>Created</Table.ColumnHeader>
                      <Table.ColumnHeader textAlign="end">
                        Actions
                      </Table.ColumnHeader>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {pendingQueries.data.map((query) => {
                      // Parse candidates JSON (temporary workaround for type mismatch)
                      let candidates: Array<{
                        product_id: string
                        confidence: number
                      }> = []
                      try {
                        candidates = query.candidates
                          ? JSON.parse(query.candidates)
                          : []
                      } catch (_e) {
                        candidates = []
                      }

                      return (
                        <Table.Row key={query.id}>
                          <Table.Cell>
                            <Button
                              variant="subtle"
                              size="xs"
                              px={2}
                              py={1}
                              onClick={() =>
                                navigate({
                                  to: "/matcher",
                                  search: {
                                    text: query.original_text,
                                    backend: query.backend,
                                    threshold: query.threshold,
                                  },
                                })
                              }
                            >
                              {query.original_text}
                            </Button>
                          </Table.Cell>
                          <Table.Cell>
                            <Code fontSize="sm" variant="surface">
                              {query.normalized_text}
                            </Code>
                          </Table.Cell>
                          <Table.Cell>
                            <Badge variant="outline">{query.backend}</Badge>
                          </Table.Cell>
                          <Table.Cell>
                            {candidates.length > 0 ? (
                              <VStack gap={1} align="start">
                                {candidates
                                  .slice(0, 2)
                                  .map((candidate, idx) => (
                                    <HStack key={idx} gap={2}>
                                      <ProductIdBadge
                                        productId={candidate.product_id}
                                        backend={query.backend}
                                        size="sm"
                                      />
                                      <Text fontSize="xs" color="fg.subtle">
                                        {(candidate.confidence * 100).toFixed(
                                          1,
                                        )}
                                        %
                                      </Text>
                                    </HStack>
                                  ))}
                                {candidates.length > 2 && (
                                  <Text fontSize="xs" color="fg.subtle">
                                    +{candidates.length - 2} more
                                  </Text>
                                )}
                              </VStack>
                            ) : (
                              <Text fontSize="sm" color="fg.muted">
                                No candidates
                              </Text>
                            )}
                          </Table.Cell>
                          <Table.Cell>
                            <Badge colorPalette={getStatusColor(query.status)}>
                              {query.status}
                            </Badge>
                          </Table.Cell>
                          <Table.Cell color="fg.muted" fontSize="sm">
                            {new Date(query.created_at).toLocaleDateString() +
                              " " +
                              new Date(query.created_at).toLocaleTimeString(
                                [],
                                {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                  second: "2-digit",
                                },
                              )}
                          </Table.Cell>
                          <Table.Cell>
                            <HStack gap={2} justify="end">
                              {query.status === "pending" && (
                                <Button
                                  size="sm"
                                  colorScheme="blue"
                                  onClick={() => handleResolveClick(query)}
                                >
                                  Resolve
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="outline"
                                colorScheme="red"
                                onClick={() => deleteMutation.mutate(query.id)}
                                loading={deletingItemId === query.id}
                              >
                                Delete
                              </Button>
                            </HStack>
                          </Table.Cell>
                        </Table.Row>
                      )
                    })}
                  </Table.Body>
                </Table.Root>
              </Box>
            )}

            {/* Pagination Controls */}
            {pendingQueries?.data?.length ? (
              <Box pt={4} borderTop="1px solid" borderColor="border.muted">
                <HStack justify="space-between" align="center">
                  <Text fontSize="sm" color="fg.muted">
                    Showing {currentPage * itemsPerPage + 1}-
                    {Math.min(
                      (currentPage + 1) * itemsPerPage,
                      currentPage * itemsPerPage + pendingQueries.data.length,
                    )}{" "}
                    of {pendingQueries.count} queries
                  </Text>
                  <HStack gap={2}>
                    <IconButton
                      size="sm"
                      variant="outline"
                      disabled={currentPage === 0}
                      onClick={() => setCurrentPage(0)}
                      aria-label="First page"
                    >
                      <FiChevronsLeft />
                    </IconButton>
                    <IconButton
                      size="sm"
                      variant="outline"
                      disabled={currentPage === 0}
                      onClick={() => setCurrentPage(currentPage - 1)}
                      aria-label="Previous page"
                    >
                      <FiChevronLeft />
                    </IconButton>
                    <Text fontSize="sm" color="fg.muted">
                      Page {currentPage + 1} of{" "}
                      {Math.ceil(pendingQueries.count / itemsPerPage)}
                    </Text>
                    <IconButton
                      size="sm"
                      variant="outline"
                      disabled={
                        (currentPage + 1) * itemsPerPage >= pendingQueries.count
                      }
                      onClick={() => setCurrentPage(currentPage + 1)}
                      aria-label="Next page"
                    >
                      <FiChevronRight />
                    </IconButton>
                    <IconButton
                      size="sm"
                      variant="outline"
                      disabled={
                        (currentPage + 1) * itemsPerPage >= pendingQueries.count
                      }
                      onClick={() =>
                        setCurrentPage(
                          Math.ceil(pendingQueries.count / itemsPerPage) - 1,
                        )
                      }
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

      <Dialog.Root
        open={isOpen}
        onOpenChange={(e) => !e.open && setIsOpen(false)}
        size="lg"
      >
        <Portal>
          <Dialog.Backdrop />
          <Dialog.Positioner>
            <Dialog.Content>
              <form onSubmit={handleSubmit(onSubmit)}>
                <Dialog.Header pb={4}>
                  <VStack gap={3} align="stretch" width="full">
                    <HStack justify="space-between">
                      <Dialog.Title fontSize="lg" fontWeight="bold">
                        Resolve Unmatched Query
                      </Dialog.Title>
                      <Dialog.CloseTrigger asChild>
                        <CloseButton size="sm" />
                      </Dialog.CloseTrigger>
                    </HStack>
                    {selectedQuery && (
                      <Box>
                        <Text
                          fontSize="sm"
                          fontWeight="semibold"
                          color="fg.muted"
                          mb={2}
                        >
                          Unmatched Query
                        </Text>
                        <QueryCard
                          originalText={selectedQuery.original_text}
                          normalizedText={selectedQuery.normalized_text}
                          backend={selectedQuery.backend}
                          createdAt={selectedQuery.created_at}
                          onOriginalTextClick={() =>
                            navigate({
                              to: "/matcher",
                              search: {
                                text: selectedQuery.original_text,
                                backend: selectedQuery.backend,
                                threshold: selectedQuery.threshold,
                              },
                            })
                          }
                        />
                      </Box>
                    )}
                  </VStack>
                </Dialog.Header>
                <Dialog.Body py={4}>
                  <VStack gap={5} align="stretch">
                    <Field label="Action">
                      <SelectRoot
                        collection={actionCollection}
                        value={[action]}
                        onValueChange={(e) =>
                          setValue("action", e.value[0] as "assign" | "ignore")
                        }
                        size="lg"
                        width="full"
                      >
                        <SelectTrigger>
                          <SelectValueText placeholder="Select action" />
                        </SelectTrigger>
                        <SelectContent>
                          {actionCollection.items.map((item) => (
                            <SelectItem key={item.value} item={item}>
                              {item.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </SelectRoot>
                    </Field>

                    {action === "assign" &&
                      selectedQuery &&
                      (() => {
                        let candidates: Array<{
                          product_id: string
                          confidence: number
                        }> = []
                        try {
                          candidates = selectedQuery.candidates
                            ? JSON.parse(selectedQuery.candidates)
                            : []
                        } catch (_e) {
                          candidates = []
                        }

                        return (
                          candidates.length > 0 && (
                            <Field label="Suggested Candidates" width="full">
                              <VStack gap={3} align="stretch" width="full">
                                <Text fontSize="sm" color="gray.600">
                                  Click on a candidate to select it:
                                </Text>
                                {candidates
                                  .slice(0, settings?.max_candidates || 5)
                                  .map((candidate, idx) => {
                                    const candidateProduct = (
                                      products as any
                                    )?.data?.find(
                                      (p: ExternalProduct) =>
                                        p.id === candidate.product_id,
                                    )
                                    return candidateProduct ? (
                                      <ProductCard
                                        key={idx}
                                        product={candidateProduct}
                                        backend={selectedQuery.backend}
                                        confidence={candidate.confidence}
                                        isSelected={
                                          selectedProduct?.id ===
                                          candidate.product_id
                                        }
                                        onClick={() => {
                                          setSelectedProduct(candidateProduct)
                                        }}
                                      />
                                    ) : (
                                      <Box
                                        key={idx}
                                        p={4}
                                        borderWidth="1px"
                                        borderRadius="md"
                                        bg="bg.subtle"
                                      >
                                        <Text fontSize="sm" color="fg.muted">
                                          Product {candidate.product_id} not
                                          found (confidence:{" "}
                                          {(candidate.confidence * 100).toFixed(
                                            1,
                                          )}
                                          %)
                                        </Text>
                                      </Box>
                                    )
                                  })}
                              </VStack>
                            </Field>
                          )
                        )
                      })()}

                    {action === "assign" && (
                      <Field
                        label={
                          selectedProduct
                            ? "Selected Product"
                            : "Or Search for Product"
                        }
                        invalid={action === "assign" && !selectedProduct}
                        errorText={
                          action === "assign" && !selectedProduct
                            ? "Please select a product"
                            : undefined
                        }
                      >
                        <VStack gap={2} align="stretch" width="full">
                          {!selectedProduct && (
                            <Input
                              placeholder="Search products by name, ID, or alias..."
                              value={productSearch}
                              onChange={(
                                e: React.ChangeEvent<HTMLInputElement>,
                              ) => setProductSearch(e.target.value)}
                              autoFocus={action === "assign"}
                              size="lg"
                              width="full"
                              px={4}
                              py={3}
                            />
                          )}
                          {selectedProduct && (
                            <Alert.Root status="success">
                              <Alert.Indicator />
                              <VStack gap={1} align="stretch">
                                <Text fontWeight="bold">
                                  {selectedProduct.aliases?.[0] ||
                                    selectedProduct.id}
                                </Text>
                                <Text fontSize="sm" color="gray.600">
                                  ID: {selectedProduct.id}
                                </Text>
                                {selectedProduct.aliases &&
                                  selectedProduct.aliases.length > 1 && (
                                    <Text fontSize="xs" color="gray.500">
                                      Aliases:{" "}
                                      {selectedProduct.aliases
                                        .slice(1)
                                        .join(", ")}
                                    </Text>
                                  )}
                              </VStack>
                            </Alert.Root>
                          )}
                          {productSearch && !selectedProduct && (
                            <Box>
                              <Text fontSize="xs" color="gray.500" mb={2}>
                                {isLoadingProducts
                                  ? "Loading..."
                                  : `${filteredProducts.length} product(s) found`}
                              </Text>
                              <Box
                                maxH="300px"
                                overflowY="auto"
                                border="1px solid"
                                borderColor="border.muted"
                                borderRadius="md"
                                bg="bg.panel"
                                boxShadow="sm"
                                width="full"
                              >
                                {isLoadingProducts ? (
                                  <HStack justify="center" p={4}>
                                    <Spinner size="sm" />
                                    <Text fontSize="sm">
                                      Loading products...
                                    </Text>
                                  </HStack>
                                ) : filteredProducts.length > 0 ? (
                                  filteredProducts.map(
                                    (
                                      product: ExternalProduct,
                                      index: number,
                                    ) => (
                                      <Box
                                        key={product.id}
                                        p={3}
                                        borderBottom={
                                          index < filteredProducts.length - 1
                                            ? "1px solid"
                                            : "none"
                                        }
                                        borderColor="border.muted"
                                        cursor="pointer"
                                        bg="bg.muted"
                                        _hover={{
                                          bg: "bg.emphasized",
                                          borderColor: "border.emphasized",
                                        }}
                                        _focus={{
                                          bg: "bg.emphasized",
                                          borderColor: "border.emphasized",
                                        }}
                                        tabIndex={0}
                                        onClick={() => {
                                          setSelectedProduct(product)
                                          setProductSearch("")
                                        }}
                                        onKeyDown={(e) => {
                                          if (
                                            e.key === "Enter" ||
                                            e.key === " "
                                          ) {
                                            e.preventDefault()
                                            setSelectedProduct(product)
                                            setProductSearch("")
                                          }
                                        }}
                                      >
                                        <VStack gap={1} align="stretch">
                                          <HStack justify="space-between">
                                            <Text
                                              fontWeight="medium"
                                              fontSize="sm"
                                            >
                                              {product.aliases?.[0] ||
                                                product.id}
                                            </Text>
                                            <Badge size="sm" colorScheme="blue">
                                              {product.id}
                                            </Badge>
                                          </HStack>
                                          {product.description && (
                                            <Text
                                              fontSize="xs"
                                              color="gray.600"
                                              style={{
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                display: "-webkit-box",
                                                WebkitLineClamp: 2,
                                                WebkitBoxOrient: "vertical",
                                              }}
                                            >
                                              {product.description}
                                            </Text>
                                          )}
                                          {product.category && (
                                            <Badge
                                              size="xs"
                                              colorScheme="green"
                                              alignSelf="flex-start"
                                            >
                                              {product.category}
                                            </Badge>
                                          )}
                                          {product.aliases &&
                                            product.aliases.length > 1 && (
                                              <Text
                                                fontSize="xs"
                                                color="gray.500"
                                                style={{
                                                  overflow: "hidden",
                                                  textOverflow: "ellipsis",
                                                  whiteSpace: "nowrap",
                                                }}
                                              >
                                                Aliases:{" "}
                                                {product.aliases
                                                  .slice(1)
                                                  .join(", ")}
                                              </Text>
                                            )}
                                        </VStack>
                                      </Box>
                                    ),
                                  )
                                ) : (
                                  <Box p={4} textAlign="center">
                                    <Text fontSize="sm" color="gray.500">
                                      No products found matching "
                                      {productSearch}"
                                    </Text>
                                    <Text fontSize="xs" color="gray.400" mt={1}>
                                      Try searching by product name, ID, or
                                      alias
                                    </Text>
                                  </Box>
                                )}
                              </Box>
                            </Box>
                          )}
                          {selectedProduct && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setSelectedProduct(null)
                                setProductSearch("")
                              }}
                            >
                              Clear Selection
                            </Button>
                          )}
                        </VStack>
                      </Field>
                    )}

                    {action === "assign" && (
                      <Field label="Product Alias">
                        <Input
                          {...register("custom_alias")}
                          placeholder="Alias to add to the selected product"
                          size="lg"
                          width="full"
                          px={4}
                          py={3}
                        />
                        <Text fontSize="xs" color="fg.muted" mt={1}>
                          This alias will be added to the selected product for
                          future matching
                        </Text>
                      </Field>
                    )}
                  </VStack>
                </Dialog.Body>

                <Dialog.Footer pt={4}>
                  <VStack gap={3} align="stretch" width="full">
                    {resolveMutation.isError && (
                      <Alert.Root status="error">
                        <Alert.Indicator />
                        <Alert.Description>
                          {getErrorMessage(resolveMutation.error)}
                        </Alert.Description>
                      </Alert.Root>
                    )}
                    <HStack justify="space-between" width="full">
                      <Text fontSize="xs" color="fg.muted">
                        Press ESC to cancel • Ctrl+Enter to resolve
                      </Text>
                      <HStack gap={3}>
                        <Button
                          variant="outline"
                          onClick={() => setIsOpen(false)}
                        >
                          Cancel
                        </Button>
                        <Button
                          type="submit"
                          colorScheme="blue"
                          loading={resolveMutation.isPending}
                          disabled={action === "assign" && !selectedProduct}
                        >
                          {action === "assign"
                            ? "Add Alias to Product"
                            : "Mark as Ignored"}
                        </Button>
                      </HStack>
                    </HStack>
                  </VStack>
                </Dialog.Footer>
              </form>
            </Dialog.Content>
          </Dialog.Positioner>
        </Portal>
      </Dialog.Root>
    </Container>
  )
}

export const Route = createFileRoute("/_layout/pending")({
  component: PendingItems,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      queryId: search.queryId as string | undefined,
    }
  },
})
