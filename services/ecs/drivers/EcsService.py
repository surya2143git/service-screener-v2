import botocore
from services.Evaluator import Evaluator

class EcsService(Evaluator):
    def __init__(self, service, cluster, ecs_client):
        super().__init__()
        self.service = service
        self.cluster = cluster
        self.ecs_client = ecs_client
        self.service_name = service['serviceName']
        self.service_arn = service['serviceArn']
        
        self.addII('serviceName', self.service_name)
        self.addII('serviceArn', self.service_arn)
        self.addII('status', service.get('status'))
        self.addII('runningCount', service.get('runningCount', 0))
        self.addII('desiredCount', service.get('desiredCount', 0))
        self.addII('launchType', service.get('launchType', 'Unknown'))
        
        self._resourceName = self.service_name
        self.init()
    
    def _checkServiceLogging(self):
        """Check if service has proper logging configuration"""
        task_definition_arn = self.service.get('taskDefinition')
        if not task_definition_arn:
            self.results['ServiceLogging'] = [0, 'No task definition found']
            return
        
        try:
            response = self.ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
            task_def = response.get('taskDefinition', {})
            container_definitions = task_def.get('containerDefinitions', [])
            
            has_logging = False
            for container in container_definitions:
                log_config = container.get('logConfiguration')
                if log_config and log_config.get('logDriver'):
                    has_logging = True
                    break
            
            if has_logging:
                self.results['ServiceLogging'] = [1, 'Logging configured']
            else:
                self.results['ServiceLogging'] = [-1, 'No logging configuration']
                
        except botocore.exceptions.ClientError as e:
            self.results['ServiceLogging'] = [0, f'Error checking task definition: {e.response["Error"]["Code"]}']
    
    def _checkServiceSecurity(self):
        """Check if service uses security groups and subnets properly"""
        network_config = self.service.get('networkConfiguration', {})
        awsvpc_config = network_config.get('awsvpcConfiguration', {})
        
        if not awsvpc_config:
            self.results['NetworkSecurity'] = [0, 'No network configuration (EC2 launch type)']
            return
        
        security_groups = awsvpc_config.get('securityGroups', [])
        subnets = awsvpc_config.get('subnets', [])
        assign_public_ip = awsvpc_config.get('assignPublicIp', 'DISABLED')
        
        issues = []
        if not security_groups:
            issues.append('No security groups')
        if not subnets:
            issues.append('No subnets')
        if assign_public_ip == 'ENABLED':
            issues.append('Public IP assigned')
        
        if issues:
            self.results['NetworkSecurity'] = [-1, f'Issues: {", ".join(issues)}']
        else:
            self.results['NetworkSecurity'] = [1, 'Properly configured']
    
    def _checkServiceScaling(self):
        """Check if service has auto scaling configured"""
        desired_count = self.service.get('desiredCount', 0)
        running_count = self.service.get('runningCount', 0)
        
        # Check if service is using capacity providers (indicates auto scaling)
        capacity_provider_strategy = self.service.get('capacityProviderStrategy', [])
        
        if capacity_provider_strategy:
            self.results['AutoScaling'] = [1, 'Capacity provider strategy configured']
        elif desired_count > 1:
            self.results['AutoScaling'] = [0, f'Multiple tasks ({desired_count}) but no auto scaling']
        else:
            self.results['AutoScaling'] = [-1, 'Single task, no auto scaling']
    
    def _checkServiceHealthChecks(self):
        """Check if service has health checks configured"""
        health_check_grace_period = self.service.get('healthCheckGracePeriodSeconds')
        load_balancers = self.service.get('loadBalancers', [])
        
        if load_balancers and health_check_grace_period is not None:
            self.results['HealthChecks'] = [1, f'Health checks with {health_check_grace_period}s grace period']
        elif load_balancers:
            self.results['HealthChecks'] = [0, 'Load balancer configured but no health check grace period']
        else:
            self.results['HealthChecks'] = [-1, 'No load balancer health checks']
    
    def _checkTaskDefinitionSecurity(self):
        """Check task definition security settings"""
        task_definition_arn = self.service.get('taskDefinition')
        if not task_definition_arn:
            self.results['TaskSecurity'] = [0, 'No task definition found']
            return
        
        try:
            response = self.ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
            task_def = response.get('taskDefinition', {})
            
            issues = []
            
            # Check if running as root
            container_definitions = task_def.get('containerDefinitions', [])
            for container in container_definitions:
                user = container.get('user')
                if not user or user == 'root' or user == '0':
                    issues.append(f'{container.get("name", "container")} runs as root')
                
                # Check for privileged mode
                if container.get('privileged'):
                    issues.append(f'{container.get("name", "container")} runs in privileged mode')
            
            # Check network mode
            network_mode = task_def.get('networkMode')
            if network_mode == 'host':
                issues.append('Uses host network mode')
            
            if issues:
                self.results['TaskSecurity'] = [-1, f'Security issues: {"; ".join(issues)}']
            else:
                self.results['TaskSecurity'] = [1, 'No security issues found']
                
        except botocore.exceptions.ClientError as e:
            self.results['TaskSecurity'] = [0, f'Error checking task definition: {e.response["Error"]["Code"]}']