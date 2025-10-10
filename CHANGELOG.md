# [1.9.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.8.2...v1.9.0) (2025-10-10)


### Features

* add frontend dependency on healthy backend ([b9aca96](https://github.com/miguelangel-nubla/product-matcher/commit/b9aca9692c897b9c930b91964745928d730fb09f))
* standardize backend to use port 80 internally ([dc90187](https://github.com/miguelangel-nubla/product-matcher/commit/dc90187efc7eba40384475078b61a7102a52a45c))

## [1.8.2](https://github.com/miguelangel-nubla/product-matcher/compare/v1.8.1...v1.8.2) (2025-10-10)


### Bug Fixes

* remove prestart debugging from playwright workflow ([cb8a619](https://github.com/miguelangel-nubla/product-matcher/commit/cb8a619fc3874b141411d8c9c78a449cf5b795c1))

## [1.8.1](https://github.com/miguelangel-nubla/product-matcher/compare/v1.8.0...v1.8.1) (2025-10-10)


### Bug Fixes

* simplify frontend Dockerfile and fix entrypoint shell ([571e00f](https://github.com/miguelangel-nubla/product-matcher/commit/571e00f3adaca0c1f3c949894b5504f458dc0e2d))

# [1.8.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.7.5...v1.8.0) (2025-10-10)


### Features

* implement file-based logging and fix test database initialization ([f09a4ff](https://github.com/miguelangel-nubla/product-matcher/commit/f09a4ff86f486cf601aa7d7584dce3bd998964db))

## [1.7.5](https://github.com/miguelangel-nubla/product-matcher/compare/v1.7.4...v1.7.5) (2025-10-10)


### Bug Fixes

* add default backends.yaml and fix gitignore scope ([51cb22c](https://github.com/miguelangel-nubla/product-matcher/commit/51cb22c4321a87baa4fa9c5294f1d60007dde59d))

## [1.7.4](https://github.com/miguelangel-nubla/product-matcher/compare/v1.7.3...v1.7.4) (2025-10-10)


### Bug Fixes

* ensure prestart works with built-in config ([5da4575](https://github.com/miguelangel-nubla/product-matcher/commit/5da4575a3c993c441a564ae47c4030ae30d781db))
* resolve CI test failures with backends config ([0741b17](https://github.com/miguelangel-nubla/product-matcher/commit/0741b17b878f0930ca8f171dc5c89fcc81e52108))

## [1.7.3](https://github.com/miguelangel-nubla/product-matcher/compare/v1.7.2...v1.7.3) (2025-10-10)


### Bug Fixes

* resolve permission issues and rename dev compose file ([3eca80b](https://github.com/miguelangel-nubla/product-matcher/commit/3eca80ba8b6ca549425381758df38c34ca3d91fa))

## [1.7.2](https://github.com/miguelangel-nubla/product-matcher/compare/v1.7.1...v1.7.2) (2025-10-10)


### Performance Improvements

* reduce Docker image sizes by 48-63% ([cf7e59f](https://github.com/miguelangel-nubla/product-matcher/commit/cf7e59fdf48d7bd45f6b57e19177b76e69935237))

## [1.7.1](https://github.com/miguelangel-nubla/product-matcher/compare/v1.7.0...v1.7.1) (2025-10-10)


### Bug Fixes

* enable runtime VITE_API_URL configuration in frontend Docker image ([2ed1b36](https://github.com/miguelangel-nubla/product-matcher/commit/2ed1b36c4a563f319697412ea83f2667856a09f2))


### Reverts

* downgrade Playwright Docker image to v1.55.0 ([1432a5d](https://github.com/miguelangel-nubla/product-matcher/commit/1432a5dc5253009cc515ce98b3cc3e4968b2befb))

# [1.7.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.6.0...v1.7.0) (2025-10-09)


### Features

* expand test coverage to 71% with comprehensive test suites ([357d051](https://github.com/miguelangel-nubla/product-matcher/commit/357d051d6694cf24d069e9e19997fa1c1ecf9585))
* improve test coverage from 58% to 76% and fix threshold logging bug ([7a39809](https://github.com/miguelangel-nubla/product-matcher/commit/7a398098ec3fd493518f66ce8bc47f32d9f1f3bf))

# [1.6.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.5.5...v1.6.0) (2025-10-09)


### Features

* reorganize backend config structure to user subdirectory ([e8c39f5](https://github.com/miguelangel-nubla/product-matcher/commit/e8c39f5cfd17adbf96345244a241a2670d9aa3ad))


### Reverts

* backend configuration mounting issues ([180f9b5](https://github.com/miguelangel-nubla/product-matcher/commit/180f9b5f856859082a1ec3395345ee5949cb54f9))

## [1.5.5](https://github.com/miguelangel-nubla/product-matcher/compare/v1.5.4...v1.5.5) (2025-10-09)


### Bug Fixes

* resolve backend configuration mounting issues ([55c3b78](https://github.com/miguelangel-nubla/product-matcher/commit/55c3b78b77bbaafd605c1fb8e8791402a7c51abd))

## [1.5.4](https://github.com/miguelangel-nubla/product-matcher/compare/v1.5.3...v1.5.4) (2025-10-09)


### Bug Fixes

* correct bash syntax in debug workflow ([ede2cd9](https://github.com/miguelangel-nubla/product-matcher/commit/ede2cd9fd1c208f275f7dd8cafc3b805848bea2c))

## [1.5.3](https://github.com/miguelangel-nubla/product-matcher/compare/v1.5.2...v1.5.3) (2025-10-09)


### Bug Fixes

* restore original health check timeouts ([dcf78c6](https://github.com/miguelangel-nubla/product-matcher/commit/dcf78c6adeb22b1157a1cdfd16b4173cf512903b))

## [1.5.2](https://github.com/miguelangel-nubla/product-matcher/compare/v1.5.1...v1.5.2) (2025-10-09)


### Bug Fixes

* increase backend health check timeouts for CI stability ([acc9bb4](https://github.com/miguelangel-nubla/product-matcher/commit/acc9bb457614a2ec3a60798d4b93e56e83524a7b))

## [1.5.1](https://github.com/miguelangel-nubla/product-matcher/compare/v1.5.0...v1.5.1) (2025-10-09)


### Bug Fixes

* wait for backend health check before running Playwright tests ([5f4d7e1](https://github.com/miguelangel-nubla/product-matcher/commit/5f4d7e1ff4bc91e839b3b9733d5e80433f4887d2))

# [1.5.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.4.0...v1.5.0) (2025-10-09)


### Features

* add dynamic environment variable injection for frontend Docker builds ([4be9dfd](https://github.com/miguelangel-nubla/product-matcher/commit/4be9dfd35a56c81d4bc39e4291ea454753aa3496))

# [1.4.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.3.4...v1.4.0) (2025-10-09)


### Features

* suppress health check log spam with configurable log level ([714ddb4](https://github.com/miguelangel-nubla/product-matcher/commit/714ddb4e0e7ed21e719e17062b2a05b2b9d02565))

## [1.3.4](https://github.com/miguelangel-nubla/product-matcher/compare/v1.3.3...v1.3.4) (2025-10-08)


### Bug Fixes

* resolve debug info validation error in matching API ([da82ece](https://github.com/miguelangel-nubla/product-matcher/commit/da82eceff0b77c6694feb35ea4a40b031d933ef9))

## [1.3.3](https://github.com/miguelangel-nubla/product-matcher/compare/v1.3.2...v1.3.3) (2025-10-08)


### Bug Fixes

* remove docker compose test step from PR workflow ([9042b85](https://github.com/miguelangel-nubla/product-matcher/commit/9042b85e0134730ffce712f544dfc4be791d58db))

## [1.3.2](https://github.com/miguelangel-nubla/product-matcher/compare/v1.3.1...v1.3.2) (2025-10-08)


### Bug Fixes

* use docker-compose.dev.yml for testing in CI ([48f78c4](https://github.com/miguelangel-nubla/product-matcher/commit/48f78c43e4784b4b810b49f6b715311732f1bbef))

## [1.3.1](https://github.com/miguelangel-nubla/product-matcher/compare/v1.3.0...v1.3.1) (2025-10-08)


### Bug Fixes

* add missing uv and Node.js setup in build workflow ([ca073c5](https://github.com/miguelangel-nubla/product-matcher/commit/ca073c598e7f16420012ece3508bb74e437871b6))

# [1.3.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.2.2...v1.3.0) (2025-10-08)


### Features

* add API client generation to Docker build workflow ([d88224f](https://github.com/miguelangel-nubla/product-matcher/commit/d88224f4c3acf8840b3e87779d7caa1bd35d5cb7))

## [1.2.2](https://github.com/miguelangel-nubla/product-matcher/compare/v1.2.1...v1.2.2) (2025-10-08)


### Bug Fixes

* correct semantic-release action outputs for Docker image building ([6f4af5e](https://github.com/miguelangel-nubla/product-matcher/commit/6f4af5ee5de2d3827abb81a181c69827c328babe))

## [1.2.1](https://github.com/miguelangel-nubla/product-matcher/compare/v1.2.0...v1.2.1) (2025-10-08)


### Bug Fixes

* remove volume mount from prestart service to allow backends.yaml creation ([f85f1b7](https://github.com/miguelangel-nubla/product-matcher/commit/f85f1b763b2e2ebf203b5b08f582be3cf88cf9a8))

# [1.2.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.1.2...v1.2.0) (2025-10-08)


### Features

* add debugging info to Playwright CI workflow ([6b97635](https://github.com/miguelangel-nubla/product-matcher/commit/6b9763507e5a561edcd8dce0fc771d0531f94af4))

## [1.1.2](https://github.com/miguelangel-nubla/product-matcher/compare/v1.1.1...v1.1.2) (2025-10-08)


### Bug Fixes

* update pre-commit config and fix failing tests ([65a02b2](https://github.com/miguelangel-nubla/product-matcher/commit/65a02b2719b800af5a1766ba9adc16c59dad7ba0))

## [1.1.1](https://github.com/miguelangel-nubla/product-matcher/compare/v1.1.0...v1.1.1) (2025-10-08)


### Bug Fixes

* update UV to latest version in CI workflows ([db8acf1](https://github.com/miguelangel-nubla/product-matcher/commit/db8acf129d8b4e42ebf507c4f32a82c47ee6ce77))

# [1.1.0](https://github.com/miguelangel-nubla/product-matcher/compare/v1.0.0...v1.1.0) (2025-10-08)


### Features

* implement proper DebugStep type and fix email functionality ([5d3ef39](https://github.com/miguelangel-nubla/product-matcher/commit/5d3ef39d54d3f69f50986741337d178f37f9365d))

# 1.0.0 (2025-10-08)


### Bug Fixes

* add required permissions for semantic-release ([ea089c2](https://github.com/miguelangel-nubla/product-matcher/commit/ea089c2e8f6d6d37c30a8c332da42c4f2785a710))
* use uv run for linting tools in lint script ([5252b88](https://github.com/miguelangel-nubla/product-matcher/commit/5252b8856597f98aae4ce291cb936f9a0902bb97))


### Features

* add development compose with mailcatcher for email testing ([4b147e4](https://github.com/miguelangel-nubla/product-matcher/commit/4b147e4e5c961f18a4ba0762c5440c7f27f3892a))
