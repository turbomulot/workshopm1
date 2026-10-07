# PKI du groupe Sentinel-X

Les certificats qui permettent de chiffrer et d'authentifier les échanges entre le boîtier ESP8266, le broker MQTT et le dashboard. Exigence « Sécurisation des flux » du sujet.

## Générer

```bash
cp security/.env.example security/.env    # une fois : GROUP_NUMBER et SERVER_IP
bash security/pki/make-pki.sh
```

`SERVER_IP` est l'adresse du PC serveur sur le Wi-Fi de table, à fixer avec l'infra **avant** de générer : elle est inscrite dans les certificats.

## Ce que ça produit (dans `security/pki/certs/`, ignoré par Git)

| Fichier | Usage | À qui |
| --- | --- | --- |
| `ca.crt` | Autorité du groupe : sert à vérifier tous les certificats | Dev (firmware), infra, clients de test |
| `ca.key` | Clé privée de l'autorité : permet de fabriquer des certificats | Personne : clé USB du responsable cyber, puis supprimée du PC |
| `broker/broker.crt` + `.key` | Identité du broker MQTT (MQTTS) | Infra |
| `web/web.crt` + `.key` | Identité du proxy HTTPS du dashboard | Infra |

Remise à l'infra et au dev : de la main à la main (clé USB), jamais par Git ni par message.

## Pourquoi ECDSA et pas RSA

Sur l'ESP8266, la poignée de main TLS prend environ 1 s en ECDSA P-256 contre 3 à 5 s en RSA 2048, et consomme beaucoup moins de RAM. C'est ce qui fait tenir le TLS sur un microcontrôleur.

## Pourquoi l'IP est dans le certificat

Le boîtier se connecte au broker par son IP. Sa pile TLS (BearSSL) vérifie que le nom demandé figure dans le certificat (champ SubjectAltName). Sans l'IP, la connexion est refusée : c'est voulu, c'est ce qui empêche un faux broker de se faire passer pour le vrai.

## Durée de validité et renouvellement

CA 90 jours, certificats 30 jours : largement assez pour le workshop, et une durée courte limite les dégâts en cas de fuite. Pour tout refaire (fuite, changement d'IP) : `bash security/pki/make-pki.sh --force`, puis redonner les certificats à l'infra et re-flasher le boîtier.
