# -*- mode: ruby -*-
# vi: set ft=ruby :

# Parse .env into a hash
env = {}
env_file = File.join(__dir__, '.env')
File.readlines(env_file).each do |line|
  line.strip!
  next if line.empty? || line.start_with?('#')
  k, v = line.split('=', 2)
  env[k.strip] = v.strip if k && v
end

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.hostname = "elk-lab"
  config.vm.boot_timeout = 600

  config.vm.network "private_network", ip: env["ELK_VM_IP"]

  # Kibana and ES are also accessible via http://192.168.56.10:5601 / :9200
  # Using alternate host ports to avoid conflicts with other local services
  config.vm.network "forwarded_port", guest: 5601, host: 5602, host_ip: "127.0.0.1"
  config.vm.network "forwarded_port", guest: 9200, host: 9201, host_ip: "127.0.0.1"
  config.vm.network "forwarded_port", guest: 5044, host: 5044
  config.vm.network "forwarded_port", guest: 5514, host: 5514
  config.vm.network "forwarded_port", guest: 8080, host: 8081

  config.vm.provider "virtualbox" do |vb|
    vb.name   = "elk-lab"
    vb.memory = env["VM_MEMORY"].to_i
    vb.cpus   = env["VM_CPUS"].to_i
    vb.customize ["modifyvm", :id, "--ioapic", "on"]
  end

  config.vm.synced_folder ".", "/vagrant"

  config.vm.provision "shell",
    path: "provision/setup.sh",
    env: env
end
