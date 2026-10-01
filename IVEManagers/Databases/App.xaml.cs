using System.Configuration;
using System.Data;
using System.Windows;

using Databases;

namespace Databases
{
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        public App()
        {
            // Initialize the application
            InitializeComponent();

            var local = MongoDBManager.CreateRemote();
        }
    }

}
