import botocore
from utils.Config import Config
from services.Service import Service
from services.ecs.drivers.EcsCluster import EcsCluster
from services.ecs.drivers.EcsService import EcsService
from utils.Tools import _pi

class Ecs(Service):
    def __init__(self, region):
        super().__init__(region)
        ssBoto = self.ssBoto
        self.ecsClient = ssBoto.client('ecs', config=self.bConfig)
        
    def getClusters(self):
        clusters = []
        try:
            paginator = self.ecsClient.get_paginator('list_clusters')
            for page in paginator.paginate():
                cluster_arns = page.get('clusterArns', [])
                if cluster_arns:
                    response = self.ecsClient.describe_clusters(clusters=cluster_arns)
                    for cluster in response.get('clusters', []):
                        if self.tags:
                            tags_response = self.ecsClient.list_tags_for_resource(resourceArn=cluster['clusterArn'])
                            tags = tags_response.get('tags', [])
                            if not self.resourceHasTags(tags):
                                continue
                        clusters.append(cluster)
        except botocore.exceptions.ClientError as e:
            print(f"Error getting clusters: {e}")
        return clusters
    
    def getServices(self, cluster_arn):
        services = []
        try:
            paginator = self.ecsClient.get_paginator('list_services')
            for page in paginator.paginate(cluster=cluster_arn):
                service_arns = page.get('serviceArns', [])
                if service_arns:
                    response = self.ecsClient.describe_services(cluster=cluster_arn, services=service_arns)
                    services.extend(response.get('services', []))
        except botocore.exceptions.ClientError as e:
            print(f"Error getting services: {e}")
        return services
    
    def advise(self):
        objs = {}
        
        clusters = self.getClusters()
        for cluster in clusters:
            cluster_name = cluster['clusterName']
            _pi('ECS::Cluster', cluster_name)
            
            obj = EcsCluster(cluster, self.ecsClient)
            obj.run(self.__class__)
            objs[f"Cluster::{cluster_name}"] = obj.getInfo()
            del obj
            
            # Check services in this cluster
            services = self.getServices(cluster['clusterArn'])
            for service in services:
                service_name = service['serviceName']
                _pi('ECS::Service', f"{cluster_name}/{service_name}")
                
                obj = EcsService(service, cluster, self.ecsClient)
                obj.run(self.__class__)
                objs[f"Service::{cluster_name}/{service_name}"] = obj.getInfo()
                del obj
        
        return objs