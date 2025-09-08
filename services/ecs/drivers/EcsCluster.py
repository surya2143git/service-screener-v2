import botocore
from services.Evaluator import Evaluator

class EcsCluster(Evaluator):
    def __init__(self, cluster, ecs_client):
        super().__init__()
        self.cluster = cluster
        self.ecs_client = ecs_client
        self.cluster_name = cluster['clusterName']
        self.cluster_arn = cluster['clusterArn']
        
        self.addII('clusterName', self.cluster_name)
        self.addII('clusterArn', self.cluster_arn)
        self.addII('status', cluster.get('status'))
        self.addII('runningTasksCount', cluster.get('runningTasksCount', 0))
        self.addII('activeServicesCount', cluster.get('activeServicesCount', 0))
        
        self._resourceName = self.cluster_name
        self.init()
    
    def _checkContainerInsights(self):
        """Check if Container Insights is enabled for monitoring"""
        settings = self.cluster.get('settings', [])
        container_insights_enabled = False
        
        for setting in settings:
            if setting.get('name') == 'containerInsights' and setting.get('value') == 'enabled':
                container_insights_enabled = True
                break
        
        if container_insights_enabled:
            self.results['ContainerInsights'] = [1, 'Enabled']
        else:
            self.results['ContainerInsights'] = [-1, 'Disabled']
    
    def _checkCapacityProviders(self):
        """Check if capacity providers are configured"""
        capacity_providers = self.cluster.get('capacityProviders', [])
        default_capacity_provider_strategy = self.cluster.get('defaultCapacityProviderStrategy', [])
        
        if capacity_providers or default_capacity_provider_strategy:
            self.results['CapacityProviders'] = [1, f"Configured: {', '.join(capacity_providers)}"]
        else:
            self.results['CapacityProviders'] = [-1, 'Not configured']
    
    def _checkClusterLogging(self):
        """Check if execute command logging is configured"""
        configuration = self.cluster.get('configuration', {})
        execute_command_config = configuration.get('executeCommandConfiguration', {})
        logging = execute_command_config.get('logging', 'NONE')
        
        if logging != 'NONE':
            self.results['ExecuteCommandLogging'] = [1, f'Enabled: {logging}']
        else:
            self.results['ExecuteCommandLogging'] = [-1, 'Disabled']
    
    def _checkClusterEncryption(self):
        """Check if execute command session encryption is enabled"""
        configuration = self.cluster.get('configuration', {})
        execute_command_config = configuration.get('executeCommandConfiguration', {})
        kms_key_id = execute_command_config.get('kmsKeyId')
        
        if kms_key_id:
            self.results['ExecuteCommandEncryption'] = [1, 'KMS encryption enabled']
        else:
            self.results['ExecuteCommandEncryption'] = [-1, 'No KMS encryption']
    
    def _checkClusterUtilization(self):
        """Check cluster resource utilization"""
        running_tasks = self.cluster.get('runningTasksCount', 0)
        active_services = self.cluster.get('activeServicesCount', 0)
        
        if running_tasks == 0 and active_services == 0:
            self.results['ClusterUtilization'] = [0, 'Empty cluster - no running tasks or services']
        elif running_tasks > 0 or active_services > 0:
            self.results['ClusterUtilization'] = [1, f'{running_tasks} tasks, {active_services} services']
        else:
            self.results['ClusterUtilization'] = [0, 'Unknown utilization']