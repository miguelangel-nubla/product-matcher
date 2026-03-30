import { Alert, Container, Heading, Tabs } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import ApiKeys from "@/components/UserSettings/ApiKeys"
import Appearance from "@/components/UserSettings/Appearance"
import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import UserInformation from "@/components/UserSettings/UserInformation"
import useAuth from "@/hooks/useAuth"

const tabsConfig = [
  { value: "my-profile", title: "My profile", component: UserInformation },
  { value: "password", title: "Password", component: ChangePassword },
  { value: "api-keys", title: "API Keys", component: ApiKeys },
  { value: "appearance", title: "Appearance", component: Appearance },
  { value: "danger-zone", title: "Danger zone", component: DeleteAccount },
]

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettings,
})

function UserSettings() {
  const { user: currentUser } = useAuth()
  const isProxyAuth = sessionStorage.getItem("proxy_auth") === "true"

  let finalTabs = tabsConfig
  if (currentUser?.is_superuser) {
    finalTabs = finalTabs.slice(0, 3)
  }
  if (isProxyAuth) {
    // Proxy auth limits users to endpoints that don't require CurrentUserJwtOnly
    // Appearance is purely local state, so it's safe.
    finalTabs = finalTabs.filter((tab) => tab.value === "appearance")
  }

  if (!currentUser) {
    return null
  }

  return (
    <Container maxW="full">
      <Heading size="lg" textAlign={{ base: "center", md: "left" }} py={12}>
        User Settings
      </Heading>

      {isProxyAuth && (
        <Alert.Root status="info" mb={8}>
          <Alert.Indicator />
          <Alert.Description>
            You are currently logged in via a Reverse Proxy / API Key. Sensitive account settings (like updating your password or managing API keys) are disabled and require a standard login.
          </Alert.Description>
        </Alert.Root>
      )}

      <Tabs.Root defaultValue="my-profile" variant="subtle">
        <Tabs.List>
          {finalTabs.map((tab) => (
            <Tabs.Trigger key={tab.value} value={tab.value}>
              {tab.title}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        {finalTabs.map((tab) => (
          <Tabs.Content key={tab.value} value={tab.value}>
            <tab.component />
          </Tabs.Content>
        ))}
      </Tabs.Root>
    </Container>
  )
}
