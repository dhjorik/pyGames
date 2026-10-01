using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using MongoDB.Driver;

namespace Databases
{
    public interface IConnectionParameters
    {
        static abstract List<string> ServerAddresses { get; }
        static abstract string ReplicaSet { get; }
        static abstract string Username { get; }
        static abstract string Password { get; }
    }
    public class LocalConnectionParameters : IConnectionParameters
    {
        public static List<string> ServerAddresses => new List<string> { "localhost:27017" };

        public static string ReplicaSet => null;
        public static string Username => "iveadmin";
        public static string Password => "ive@2021";
    }
    public class RemoteConnectionParameters : IConnectionParameters
    {
        public static List<string> ServerAddresses => new List<string> { "dc5lp-jptr-mongo1:27017", "dc5lp-jptr-mongo2:27017", "dc5lp-jptr-mongo3:27017", };

        public static string ReplicaSet => "rs0";
        public static string Username => "iveadmin";
        public static string Password => "ive@2021";
    }

    public class MongoDBManager
    {
        public MongoDBManager() { }

        // Opens a connection to MongoDB using server addresses, replica set, and credentials
        public MongoClient OpenConnection(List<string> serverAddresses, string replicaSet, string username, string password)
        {
            // Build the MongoDB connection string with authentication
            string servers = string.Join(",", serverAddresses);
            string connectionString = $"mongodb://{username}:{password}@{servers}";
            if (replicaSet is not null)
            {
                connectionString = $"{connectionString}/?replicaSet={replicaSet}";
            }
            var client = new MongoClient(connectionString);
            return client;
        }

        // Factory method for local connection (no credentials, no replica set)
        public static MongoClient CreateLocal()
        {
            string servers = string.Join(",", LocalConnectionParameters.ServerAddresses);
            string authenticator = $"{LocalConnectionParameters.Username}:{LocalConnectionParameters.Password}";
            string connectionString = $"mongodb://{authenticator}@{servers}";
            if (LocalConnectionParameters.ReplicaSet is not null)
            {
                connectionString = $"{connectionString}/?replicaSet={LocalConnectionParameters.ReplicaSet}";
            }
            return new MongoClient(connectionString);
        }

        // Factory method for remote connection
        public static MongoClient CreateRemote()
        {
            string servers = string.Join(",", RemoteConnectionParameters.ServerAddresses);
            string authenticator = $"{RemoteConnectionParameters.Username}:{RemoteConnectionParameters.Password}";
            string connectionString = $"mongodb://{authenticator}@{servers}";
            if (RemoteConnectionParameters.ReplicaSet is not null)
            {
                connectionString = $"{connectionString}/?replicaSet={RemoteConnectionParameters.ReplicaSet}";
            }
            return new MongoClient(connectionString);
        }
    }
}
