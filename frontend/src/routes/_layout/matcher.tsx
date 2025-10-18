import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Code,
  CollapsibleContent,
  CollapsibleRoot,
  CollapsibleTrigger,
  Container,
  createListCollection,
  Grid,
  Heading,
  HStack,
  Input,
  SelectContent,
  SelectItem,
  SelectRoot,
  SelectTrigger,
  SelectValueText,
  Slider,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import type {
  BackendInfo,
  DebugStep,
  GlobalSettings,
  MatchRequest,
  MatchResult,
} from "../../client"
import { MatchingService } from "../../client"
import { ProductCard } from "../../components/ProductCard"
import { QueryCard } from "../../components/QueryCard"
import { Field } from "../../components/ui/field"
import { getErrorMessage } from "../../utils/error"

interface MatchForm {
  text: string
  backend: string
  threshold: number
  createPending: boolean
}

const formatDebugStep = (
  step: DebugStep,
  index: number,
  debugSteps: DebugStep[],
) => {
  const startTime = debugSteps[0]?.timestamp || 0
  const totalMs = (step.timestamp - startTime) * 1000
  const stepMs =
    index === 0
      ? totalMs
      : (step.timestamp - debugSteps[index - 1].timestamp) * 1000

  return {
    timing: `[${totalMs.toFixed(0)}ms +${stepMs.toFixed(0)}ms]`,
    message: step.message,
    data: step.data,
  }
}

function ProductMatcher() {
  const navigate = useNavigate()
  const {
    text: searchText,
    backend: searchBackend,
    threshold: searchThreshold,
  } = useSearch({ from: "/_layout/matcher" })
  const [result, setResult] = useState<MatchResult | null>(null)
  const [lastInputText, setLastInputText] = useState<string>("")

  // Load available backends
  const { data: backends, isLoading: isLoadingBackends } = useQuery({
    queryKey: ["backends"],
    queryFn: () => MatchingService.getAvailableBackends(),
  })

  // Load global settings
  const { data: settings } = useQuery<GlobalSettings>({
    queryKey: ["matching-settings"],
    queryFn: () => MatchingService.getMatchingSettings(),
  })

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<MatchForm>({
    defaultValues: {
      text: "",
      backend: "",
      threshold: 0.8,
      createPending: true,
    },
  })

  // Update threshold when settings load
  useEffect(() => {
    if (settings) {
      setValue("threshold", settings.default_threshold)
    }
  }, [settings, setValue])

  // Set default backend to first available when backends load
  useEffect(() => {
    if (backends && backends.length > 0) {
      setValue("backend", backends[0].name)
    }
  }, [backends, setValue])

  // Auto-populate form from URL search parameters
  useEffect(() => {
    if (searchText) {
      setValue("text", searchText)
    }
    if (searchBackend) {
      setValue("backend", searchBackend)
    }
    if (searchThreshold) {
      setValue("threshold", searchThreshold)
    }
  }, [searchText, searchBackend, searchThreshold, setValue])

  const threshold = watch("threshold")
  const selectedBackend = watch("backend")

  // Create collections for select components
  const backendCollection = createListCollection({
    items:
      (backends as BackendInfo[])?.map((backend) => ({
        label: backend.description,
        value: backend.name,
      })) || [],
  })

  const matchMutation = useMutation({
    mutationFn: (data: MatchRequest & { createPending?: boolean }) =>
      MatchingService.matchProduct({ requestBody: data }),
    onSuccess: (data, variables) => {
      // If createPending is false and there's a pending_query_id, hide it from the UI
      if (variables.createPending === false && data.pending_query_id) {
        setResult({
          ...data,
          pending_query_id: null,
        })
      } else {
        setResult(data)
      }
    },
  })

  const onSubmit = (data: MatchForm) => {
    setLastInputText(data.text)
    const matchRequest: MatchRequest = {
      text: data.text,
      backend: data.backend,
      threshold: data.threshold,
      create_pending: !data.createPending, // Invert: Test Mode checked = don't create pending
      debug: true, // Always include debug info in frontend match UI
    }
    matchMutation.mutate(matchRequest)
  }

  return (
    <Container maxW="container.md" py={8}>
      <VStack gap={8} align="stretch">
        <Box>
          <Heading size="lg" mb={4}>
            Product Matcher
          </Heading>
          <Text color="gray.600">
            Match product names against external inventory systems with fuzzy
            matching and language support.
          </Text>
        </Box>

        <Card.Root>
          <Card.Body>
            <form onSubmit={handleSubmit(onSubmit)}>
              <VStack gap={6}>
                <Grid templateColumns="1fr auto" gap={3} width="100%">
                  <Field
                    label="Product Text"
                    invalid={!!errors.text}
                    errorText={errors.text?.message}
                    required
                  >
                    <Input
                      {...register("text", {
                        required: "Product text is required",
                      })}
                      placeholder="e.g., red apple, milk, cookies"
                    />
                  </Field>

                  <Field label="Test Mode" justifySelf="center">
                    <Box pt="2">
                      <Checkbox.Root defaultChecked={true} size="lg">
                        <Checkbox.HiddenInput {...register("createPending")} />
                        <Checkbox.Control>
                          <Checkbox.Indicator />
                        </Checkbox.Control>
                      </Checkbox.Root>
                    </Box>
                  </Field>
                </Grid>

                <Grid templateColumns="1fr 2fr" gap={3} width="100%">
                  <Field
                    label="Backend"
                    invalid={!!errors.backend}
                    errorText={errors.backend?.message}
                    required
                  >
                    {isLoadingBackends ? (
                      <HStack>
                        <Spinner size="sm" />
                        <Text fontSize="sm">Loading...</Text>
                      </HStack>
                    ) : (
                      <SelectRoot
                        collection={backendCollection}
                        value={[selectedBackend]}
                        onValueChange={(e) => setValue("backend", e.value[0])}
                        size="md"
                      >
                        <SelectTrigger>
                          <SelectValueText placeholder="Backend" />
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
                  </Field>

                  <Field
                    label={`Confidence Threshold: ${threshold.toFixed(2)}`}
                    width="full"
                  >
                    <VStack gap={2} align="stretch" width="full">
                      <Slider.Root
                        value={[threshold]}
                        onValueChange={(details: any) =>
                          setValue("threshold", details.value[0])
                        }
                        min={0.1}
                        max={1.0}
                        step={0.05}
                        size="lg"
                      >
                        <Slider.Control>
                          <Slider.Track>
                            <Slider.Range />
                          </Slider.Track>
                          <Slider.Thumb index={0} />
                        </Slider.Control>
                      </Slider.Root>
                      <HStack
                        justify="space-between"
                        fontSize="xs"
                        color="fg.muted"
                      >
                        <Text>0.1 (Low)</Text>
                        <Text>0.5 (Medium)</Text>
                        <Text>0.8 (High)</Text>
                        <Text>1.0 (Exact)</Text>
                      </HStack>
                    </VStack>
                  </Field>
                </Grid>

                <Button
                  type="submit"
                  colorScheme="blue"
                  size="lg"
                  width="full"
                  loading={matchMutation.isPending}
                  loadingText="Matching..."
                >
                  Match Product
                </Button>
              </VStack>
            </form>
          </Card.Body>
        </Card.Root>

        {matchMutation.error && (
          <Alert.Root status="error">
            <Alert.Indicator />
            <Alert.Title>Error</Alert.Title>
            <Alert.Description>
              {getErrorMessage(matchMutation.error)}
            </Alert.Description>
          </Alert.Root>
        )}

        {result && !matchMutation.error && !matchMutation.isPending && (
          <Card.Root>
            <Card.Body>
              <VStack gap={4} align="stretch">
                <HStack justify="space-between" align="center">
                  <Heading size="md">Results</Heading>
                  {result.success ? (
                    <Alert.Root status="success" size="sm" width="auto">
                      <Alert.Indicator />
                      <Alert.Description>
                        Product matched successfully!
                      </Alert.Description>
                    </Alert.Root>
                  ) : (
                    <Alert.Root status="warning" size="sm" width="auto">
                      <Alert.Indicator />
                      <Alert.Description>
                        {result.pending_query_id
                          ? "No match found - added to pending queue"
                          : "No match found"}
                      </Alert.Description>
                    </Alert.Root>
                  )}
                </HStack>

                <VStack gap={4} align="stretch">
                  <Box>
                    <Text
                      fontSize="sm"
                      fontWeight="semibold"
                      color="fg.muted"
                      mb={2}
                    >
                      Query
                    </Text>
                    <QueryCard
                      originalText={lastInputText}
                      normalizedText={result.normalized_input}
                      backend={selectedBackend}
                      onOriginalTextClick={() =>
                        navigate({
                          to: "/matcher",
                          search: {
                            text: lastInputText,
                            backend: selectedBackend,
                            threshold: watch("threshold"),
                          },
                        })
                      }
                    />
                  </Box>

                  {result.ignored && (
                    <Alert.Root status="info">
                      <Alert.Indicator />
                      <Alert.Description>
                        This normalized query is marked as ignored.
                      </Alert.Description>
                    </Alert.Root>
                  )}

                  {/* Show all candidates */}
                  {result.candidates && result.candidates.length > 0 ? (
                    <VStack gap={3} align="stretch">
                      <Text
                        fontWeight="semibold"
                        fontSize="sm"
                        color="fg.muted"
                      >
                        {result.success
                          ? `Matched product (${result.candidates.length} candidate${result.candidates.length > 1 ? "s" : ""} found):`
                          : `Found ${result.candidates.length} candidate${result.candidates.length > 1 ? "s" : ""}:`}
                      </Text>
                      {result.candidates.map((candidate, index) => (
                        <ProductCard
                          key={candidate.product_id}
                          id={candidate.product_id}
                          backend={selectedBackend}
                          confidence={candidate.confidence}
                          isSelected={result.success && index === 0}
                        />
                      ))}
                    </VStack>
                  ) : (
                    <ProductCard
                      product={{
                        id: "N/A",
                        aliases: ["No matches found"],
                        description:
                          "No products found in the database that match your search",
                      }}
                    />
                  )}
                </VStack>

                {result.pending_query_id && (
                  <Text fontSize="sm" color="fg.muted">
                    Query ID:{" "}
                    <Badge
                      colorScheme="orange"
                      size="sm"
                      cursor="pointer"
                      onClick={() =>
                        navigate({
                          to: "/pending",
                          search: {
                            queryId: result.pending_query_id || undefined,
                          },
                        })
                      }
                      title="Click to resolve this query"
                    >
                      {result.pending_query_id}
                    </Badge>
                  </Text>
                )}
              </VStack>
            </Card.Body>
          </Card.Root>
        )}

        {result?.debug_info && !matchMutation.isPending && (
          <Card.Root>
            <Card.Body>
              <CollapsibleRoot>
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    width="full"
                    justifyContent="space-between"
                    color="fg.muted"
                  >
                    <Text fontSize="sm" fontWeight="semibold">
                      Debug Information ({result.debug_info.length} steps,{" "}
                      {result.debug_info.length > 0
                        ? (
                            (result.debug_info[result.debug_info.length - 1]
                              ?.timestamp -
                              result.debug_info[0]?.timestamp) *
                            1000
                          ).toFixed(0)
                        : 0}
                      ms total)
                    </Text>
                    <Text fontSize="xs">▼</Text>
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <Box mt={3} p={3} bg="bg.muted" borderRadius="md">
                    <VStack gap={2} align="stretch">
                      {result.debug_info.map((step, index) => {
                        const formatted = formatDebugStep(
                          step,
                          index,
                          result.debug_info!,
                        )
                        return (
                          <Box
                            key={index}
                            p={2}
                            bg="bg.default"
                            borderRadius="sm"
                            borderLeft="2px solid"
                            borderColor="blue.500"
                          >
                            <HStack gap={4} align="flex-start">
                              <Box width="60px" flexShrink={0}>
                                <Text
                                  fontSize="xs"
                                  color="fg.muted"
                                  fontFamily="mono"
                                  textAlign="right"
                                  whiteSpace="nowrap"
                                >
                                  {`${(
                                    index === result.debug_info!.length - 1
                                      ? index === 0
                                        ? 0
                                        : (step.timestamp -
                                            result.debug_info![index - 1]
                                              .timestamp) *
                                          1000
                                      : (result.debug_info![index + 1]
                                          .timestamp -
                                          step.timestamp) *
                                        1000
                                  ).toFixed(0)}ms`}
                                </Text>
                              </Box>
                              <VStack gap={1} align="stretch" flex={1}>
                                <Text fontSize="xs" fontWeight="medium">
                                  {formatted.message}
                                </Text>
                                {Boolean(formatted.data) && (
                                  <CollapsibleRoot>
                                    <CollapsibleTrigger asChild>
                                      <Button
                                        variant="ghost"
                                        size="xs"
                                        p={1}
                                        h="auto"
                                        fontWeight="normal"
                                        color="fg.muted"
                                        justifyContent="flex-start"
                                      >
                                        <Text fontSize="2xs">Show data ▼</Text>
                                      </Button>
                                    </CollapsibleTrigger>
                                    <CollapsibleContent>
                                      <Code
                                        fontSize="2xs"
                                        bg="bg.muted"
                                        p={2}
                                        mt={1}
                                        borderRadius="xs"
                                        wordBreak="break-all"
                                        whiteSpace="pre-wrap"
                                        display="block"
                                        maxHeight="200px"
                                        overflowY="auto"
                                      >
                                        {
                                          JSON.stringify(
                                            formatted.data,
                                            null,
                                            2,
                                          ) as string
                                        }
                                      </Code>
                                    </CollapsibleContent>
                                  </CollapsibleRoot>
                                )}
                              </VStack>
                            </HStack>
                          </Box>
                        )
                      })}
                    </VStack>
                  </Box>
                </CollapsibleContent>
              </CollapsibleRoot>
            </Card.Body>
          </Card.Root>
        )}
      </VStack>
    </Container>
  )
}

export const Route = createFileRoute("/_layout/matcher")({
  component: ProductMatcher,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      text: search.text as string | undefined,
      backend: search.backend as string | undefined,
      threshold: search.threshold as number | undefined,
    }
  },
})
