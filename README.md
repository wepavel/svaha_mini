# svahaminiback

#### rye project init
```sh
rye init SvahaMiniBack
rye pin 3.10
rye sync
rye add "fastapi"

```

## RabbitMQ

#### Local developement

```sh
brew install rabbitmq
```

#### Start on mac
```sh

brew services start rabbitmq
brew services info rabbitmq

```

## Redis


#### Install on mac

```sh
brew install redis
```


```sh
redis-server
#or
brew services start redis
brew services info redis
brew services stop redis

```

#### Todo

- [x] To Cum
- [x] Implement Minio (Local/Self-hosted S3)
- [x] Instrumental upload
- [x] Vocal upload
- [ ] Additional vocal upload
- [ ] Uploading progress sending
- [ ] Settings receive
- [ ] Mix download

